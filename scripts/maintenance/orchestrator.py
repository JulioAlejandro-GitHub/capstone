"""Noninteractive state machine shared by the three public commands."""
import fcntl
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.maintenance.protected_resources import HISTORY_TABLES
from scripts.maintenance.verification import MaintenanceError, require, write_json, digest


def execute(mode, transport, report, previous=None):
    started = time.monotonic()
    summary = {'mode':mode,'started_at':datetime.now(timezone.utc).isoformat(),'status':'STARTED'}
    db = {'status':'NOT_REQUESTED','deleted_records':0}
    files = {'status':'NOT_REQUESTED','deleted_files':0}
    source = None
    db_verified = False
    restart_safe = False
    file_fenced = False
    def log(event):
        with (report/'execution.log').open('a') as stream:
            stream.write(datetime.now(timezone.utc).isoformat()+' '+event+'\n')
    try:
        log('PREFLIGHT')
        transport.discover()
        transport.inspect(artifact_only=mode=='artifacts')
        transport.stop_writers()
        source = transport.inspect(artifact_only=mode=='artifacts')
        write_json(report/'source.json',source)
        protected = transport.filesystem_state()
        write_json(report/'protected_files.json',protected)
        manifest = None
        if previous and mode == 'artifacts':
            # A later standalone cleanup has a new baseline. An older DB-only
            # report is optional ownership evidence, never a permanent stale gate.
            old = json.loads((previous/'summary.json').read_text())
            reusable = (old.get('database_verified')
                and source['snapshot']==json.loads((previous/'post_database.json').read_text())
                and source['identity']==json.loads((previous/'source.json').read_text())['identity']
                and protected==json.loads((previous/'protected_files.json').read_text())
                and digest(previous/'manifest.json')==old.get('manifest_sha256'))
            if not reusable:
                summary['prior_ownership_report_not_reused']='CURRENT_STATE_DIFFERS'
                previous=None
        if previous and mode in ('all','artifacts'):
            old = json.loads((previous/'summary.json').read_text())
            require(old['status'] in ('PARTIAL','COMPLETED','ALREADY_CLEAN') and old['database_verified'],'INVALID_RESUME_STATE')
            require(source['snapshot']==json.loads((previous/'post_database.json').read_text()),'RESUME_DATABASE_CHANGED')
            require(source['identity']==json.loads((previous/'source.json').read_text())['identity'],'RESUME_IDENTITY_CHANGED')
            require(protected==json.loads((previous/'protected_files.json').read_text()),'RESUME_PROTECTED_FILES_CHANGED')
            require(digest(previous/'manifest.json')==old['manifest_sha256'],'RESUME_MANIFEST_CHANGED')
            manifest = json.loads((previous/'manifest.json').read_text())
            db = json.loads((previous/'db_cleanup.json').read_text())
            db['resumed_without_database_cleanup'] = True
            summary['resumed_from'] = str(previous)
            db_verified = True
        else:
            manifest = transport.scan(source)
        if manifest is not None:
            write_json(report/'manifest.json',manifest)
            summary['manifest_sha256'] = digest(report/'manifest.json')
        if mode in ('all','db') and not db_verified:
            count = sum(source['snapshot']['schemas']['public'][t]['count'] for t in HISTORY_TABLES)
            log('DATABASE_PHASE')
            if count == 0:
                db = {'status':'ALREADY_CLEAN','deleted_records':0,'integrity':transport.rpc('verify')}
            else:
                db = transport.cleanup_db(source)
            require(db['status'] in ('COMPLETED','ALREADY_CLEAN'),'DATABASE_NOT_CONFIRMED')
            db_verified = True
        write_json(report/'db_cleanup.json',db)
        post = transport.inspect(artifact_only=mode=='artifacts')['snapshot']
        write_json(report/'post_database.json',post)
        if mode in ('all','artifacts'):
            log('ARTIFACT_PHASE')
            file_fenced = True
            transport.rpc('fence_files')
            files = transport.delete_files(manifest)
            # Re-scan catches files created after the manifest was frozen.
            remaining = transport.scan(source)
            require(not any(remaining[k]['files'] or remaining[k]['issues'] for k in ('host','volume')),'ARTIFACT_RESIDUE')
        require(transport.filesystem_state()==protected,'PROTECTED_FILES_CHANGED')
        if file_fenced:
            transport.rpc('unfence_files')
            file_fenced = False
        require(transport.inspect(artifact_only=mode=='artifacts')['snapshot']==post,'DATABASE_CHANGED_DURING_FILES')
        restart_safe = True
        transport.restart()
        if mode=='db':
            summary['status']=db['status']
        elif mode=='artifacts':
            summary['status']=files['status']
        else:
            summary['status']='ALREADY_CLEAN' if db['status']=='ALREADY_CLEAN' and files['status']=='NO_ARTIFACTS_FOUND' else 'COMPLETED'
        return_code = 0
    except BaseException as exc:
        code = str(exc) if isinstance(exc,MaintenanceError) else type(exc).__name__
        summary.update(status='PARTIAL' if mode=='all' and db_verified else 'ERROR',error=code)
        files = {'status':'ERROR','error':code} if db_verified or mode=='artifacts' else files
        if not db_verified and mode in ('all','db'):
            # Preserve the durable COMMIT_UNCERTAIN report from the SQL worker.
            if (report/'db_cleanup.json').exists():
                db = json.loads((report/'db_cleanup.json').read_text())
            else:
                db = {'status':'ERROR','error':code}
        log(summary['status']+' '+code)
        if file_fenced:
            try:
                transport.rpc('unfence_files')
                file_fenced = False
            except Exception:
                summary['file_fence_requires_review'] = True
        # Errors never imply rollback. Writers stay stopped unless full equality
        # with the source (and protected filesystem) can be proven again.
        if source is not None and not db_verified and db.get('status')!='COMMIT_UNCERTAIN':
            try:
                restart_safe = transport.inspect()['snapshot']==source['snapshot'] and transport.filesystem_state()==protected
                if restart_safe:
                    transport.restart()
            except Exception:
                restart_safe=False
        summary['writers_require_review']=not restart_safe
        return_code=2
    finally:
        summary.update(database_verified=db_verified,duration_seconds=round(time.monotonic()-started,3),database_status=db['status'],artifact_status=files['status'])
        write_json(report/'db_cleanup.json',db)
        journal_rows=[]
        for journal in report.glob('*journal.jsonl'):
            for line in journal.read_text().splitlines():
                try:
                    journal_rows.append(json.loads(line))
                except ValueError:
                    summary['journal_incomplete']=True
        files['confirmed_deletions_this_execution']={'files':len(journal_rows),'logical_bytes':sum(row['bytes'] for row in journal_rows)}
        write_json(report/'artifact_cleanup.json',files)
        try:
            transport.close()
        except Exception as exc:
            summary.update(status='PARTIAL' if db_verified and mode=='all' else 'ERROR',close_error=type(exc).__name__)
            return_code=2
        write_json(report/'summary.json',summary)
        log(summary['status'])
    return return_code


def main(mode):
    from scripts.maintenance.docker_transport import DockerTransport
    project=Path(__file__).resolve().parents[2]
    root=project/'var'/'maintenance'
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.umask(0o077)
    with (root/'.lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('MAINTENANCE_ALREADY_RUNNING',file=sys.stderr)
            return 2
        for _ in range(20):
            stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            report=root/stamp
            if not report.exists():
                break
            time.sleep(0.1)
        if report.exists():
            print('REPORT_TIMESTAMP_COLLISION',file=sys.stderr)
            return 2
        report.mkdir(mode=0o700)
        if len(sys.argv)!=1:
            write_json(report/'summary.json',{'status':'ERROR','error':'OPTIONS_NOT_SUPPORTED'})
            return 2
        previous=None
        if mode in ('all','artifacts'):
            for candidate in sorted(root.glob('*/summary.json'),reverse=True):
                value=json.loads(candidate.read_text())
                if mode=='all' and value.get('mode')=='all':
                    if value.get('status')=='PARTIAL':
                        previous=candidate.parent
                    break
                if mode=='artifacts' and value.get('mode')=='db' and value.get('database_verified'):
                    previous=candidate.parent
                    break
        result=execute(mode,DockerTransport(project,report),report,previous)
        summary=json.loads((report/'summary.json').read_text())
        print(summary['status']+' — '+str(report))
        return result
