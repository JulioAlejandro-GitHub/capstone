"""Bounded synchronous API reporting; failure stops calculation, never file fallback."""
from copy import deepcopy
from http.client import HTTPException as HTTPTransportError
import json
import time
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from .storage import resolve
from .event_transport import EventRejected, EventServerFailure, EventTransportFailure, EventProtocolError


class Api:
    def __init__(self,url,bearer,timeout=15):
        if not url.startswith(('https://','http://127.0.0.1:','http://localhost:')):
            raise ValueError('TLS_OR_LOOPBACK_REQUIRED')
        self.url=url.rstrip('/')+'/execution/local';self.bearer=bearer;self.timeout=timeout

    def call_event(self, payload):
        """One E10 delivery attempt. The caller may retry the exact same event.

        Legacy call()/Reports keep their existing retry policy. Do not expose
        remote error bodies, URLs or bearer credentials in delivery exceptions.
        """
        data=json.dumps(payload,allow_nan=False).encode()
        if len(data)>8*1024*1024:raise ValueError('REPORT_TOO_LARGE')
        req=Request(self.url+'/events',data=data,headers={
            'Authorization':'Bearer '+self.bearer,'Content-Type':'application/json'})
        try:
            with urlopen(req,timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            status=exc.code
            exc.close()
            if status<500:raise EventRejected(status) from None
            raise EventServerFailure(status) from None
        except (URLError,OSError,HTTPTransportError):
            raise EventTransportFailure('EVENT_DELIVERY_UNCONFIRMED') from None
        except (ValueError,UnicodeError):
            raise EventProtocolError('EVENT_RESPONSE_INVALID') from None

    def call(self,operation,payload):
        data=json.dumps(payload,allow_nan=False).encode()
        if len(data)>8*1024*1024:raise ValueError('REPORT_TOO_LARGE')
        for n in range(3):
            req=Request(self.url+'/'+operation,data=data,headers={'Authorization':'Bearer '+self.bearer,'Content-Type':'application/json'})
            try:
                with urlopen(req,timeout=self.timeout) as response:return json.load(response)
            except HTTPError as e:
                if e.code<500:raise RuntimeError('API_REJECTED_'+str(e.code)) from None
            except (URLError,TimeoutError):pass
            if n<2:time.sleep(n+1)
        raise RuntimeError('API_COMMUNICATION_UNCONFIRMED')


class Reports:
    """The existing train(repository, session, descriptor) reporting interface."""
    def __init__(self,api,job,local_artifacts):
        self.api=api;self.job=job;self.root=local_artifacts

    def envelope(self):return {k:self.job[k] for k in ('job_id','agent_id','owner')}

    def put(self,run,owner,kind,phase,key,payload):
        if str(run)!=self.job['run_id'] or str(owner)!=self.job['owner']:
            raise ValueError('LOCAL_OWNER_CONFLICT')
        payload=deepcopy(payload)
        if 'path' in payload:
            from pathlib import Path
            p=Path(payload['path']);relative=p.relative_to(Path(self.root)).as_posix()
            if resolve(self.root,relative)!=p.resolve():raise ValueError('ARTIFACT_ROOT_CONFLICT')
            payload['path']={'root_id':self.job['artifact_root_id'],'relative_path':relative}
        return self.api.call('record',{**self.envelope(),'kind':kind,'phase':phase,'key':str(key),'payload':payload})

    def records(self,run):
        if str(run)!=self.job['run_id']:raise ValueError('RUN_CONFLICT')
        return self.api.call('records',self.envelope())['records']

    def finish(self,run,owner,state,evidence=None,cause=None):
        if str(run)!=self.job['run_id'] or str(owner)!=self.job['owner'] or state!='completed':
            raise ValueError('LOCAL_FINALIZATION_CONFLICT')
        # Backend stores calculation evidence; it must NOT release the reservation here.
        return self.api.call('calculation-ended',{**self.envelope(),'evidence':evidence})
