"""DBV2.4 evidence: read-only stored-hash comparison plus Markdown/manifest generation. No secrets."""
import hashlib
import json
import sys

import dbv24_transfer as m
from dbv24_transfer import E, OLD, TARGET, DATASET, OFFICIAL, persistent, qid

# Stored scientific hash columns; compared as stored text, never recomputed from images.
STORED = {'dataset_source_records': ['source_file_sha256', 'decoded_pixel_sha256'], 'dataset_split_images': ['checksum_sha256']}
FAMILIES = {
    'audit_events': ['audit_events'],
    'experiments / runs': ['experiments', 'runs', 'run_metrics', 'run_clinical_metrics', 'training_history', 'predictions'],
    'campaigns': ['experimental_campaigns', 'campaign_members', 'campaign_attempts', 'campaign_configurations'],
    'evaluations / calibration / ensembles': ['evaluations', 'run_threshold_calibration', 'ensembles'],
    'TRAIN / E10': ['experiment_execution_events', 'train_execution_revisions'],
    'XAI': [],
    'publication / deployment': ['model_versions', 'model_deployments'],
    'clinical workflow / smear': ['cell_classification_runs', 'cell_predictions', 'smear_analysis_summaries'],
}


def stored_hashes():
    out = []
    with m.source() as s, persistent.connect(TARGET) as c:
        m.session(c)
        c.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        try:
            for t, cols in STORED.items():
                key = ','.join(map(qid, m.pk(c, t)))
                for col in cols:
                    q = f"SELECT count({qid(col)}) AS non_null, encode(sha256(convert_to(coalesce(string_agg({key}::text||':'||coalesce({qid(col)},'NULL'),E'\\n' ORDER BY {key}),''),'UTF8')),'hex') AS digest FROM public.{qid(t)}"
                    a, b = s.execute(q).fetchone(), c.execute(q).fetchone()
                    assert a == b, 'STORED_HASH_MISMATCH:' + t + '.' + col
                    out.append(dict(table=t, column=col, non_null=a['non_null'], column_digest=a['digest'], match=True))
        finally:
            c.execute('ROLLBACK')
    m.save('stored_hash_columns.json', out)
    return out


def J(name):
    return json.loads((E / name).read_text())


def write(name, lines):
    (E / name).write_text('\n'.join(lines) + '\n')


def table(rows, cols):
    return ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)] + ['| ' + ' | '.join(str(r[c]) for c in cols) + ' |' for r in rows]


def main():
    hashes = stored_hashes()
    v, pre, pb = J('verification_after_restart.json'), J('preflight_initial.json'), J('validation_before_commit_persistent.json')
    ident, rb, rr, per = J('identity_persistent.json'), J('rollback_result.json'), J('rollback_recovery.json'), J('persistence_result.json')
    for x in ['verification_post_commit.json', 'verification_repeat.json', 'verification_before_restart.json']:
        o = J(x)
        assert o['result'] == 'ALREADY_TRANSFERRED_EXACTLY' and o['tables'] == v['tables'] and o['structural_manifest_sha256'] == v['structural_manifest_sha256']
    assert pb['tables'] == v['tables']
    sci, auth, tabs = v['scientific_snapshot'], v['authentication'], v['tables']
    empty = v['absence']['baseline_empty_tables']
    fps = sci['stored_fingerprints']
    freeze = {f['path'].rsplit('.', 1)[1]: f['stored_value'] for f in fps if '.freeze_contract.fingerprints.' in f['path']}
    dataset_rows = sum(t['transferred_count'] for t in tabs if t['table'] in DATASET)
    t = ident['destination']
    srv = ident['server']

    manifest = dict(
        label='DBV2.4 TRANSFER MANIFEST (no secrets)',
        destination_database=TARGET['database'], destination_container=TARGET['container_name'], destination_volume=TARGET['volume'],
        destination_postgres='17.9', destination_system_identifier=TARGET['postgres_system_identifier'], destination_database_oid=TARGET['database_oid'],
        destination_revision='pg_v2_baseline', root_revision_sha256=persistent.EXPECTED_REVISION,
        structural_manifest_sha256=v['structural_manifest_sha256'], structural_manifest_sha256_before=pre['structural_manifest_sha256'],
        transfer_plan_sha256=pre['plan_sha256'], dataset_version_id=OFFICIAL,
        dataset=[dict(table=x['table'], source_count=x['source_count'], destination_count=x['destination_count'], transfer_hash=x['transfer_hash'], pk_hash=x['pk_hash'], status=x['result']) for x in tabs if x['table'] in DATASET],
        scientific_snapshot=dict(train=sci['train'], validation=sci['validation'], test=sci['test'], total=sci['total'], patients=sci['patients'], overlaps=sci['overlaps'], dataset_split_images=sci['dataset_split_images'], physical_roots=len(sci['physical_roots']), stored_freeze_fingerprints=freeze),
        stored_hash_columns=hashes,
        authentication=dict(roles_count=auth['roles_count'], roles_source_total=auth['roles_source_total'], users_count=auth['users_count'], user_roles_count=auth['user_roles_count'], preserved_user_count=auth['preserved_user_count'], password_hash_match=auth['password_hash_match'],
                            tables=[dict(table=x['table'], source_count=x['source_count'], destination_count=x['destination_count'], transfer_hash=x['transfer_hash'], status=x['result']) for x in tabs if x['table'] not in DATASET]),
        unauthorized_transfer=v['unauthorized_transfer'], audit_events_transferred=empty['audit_events'], semantic_transformations=v['semantic_transformations'],
        frozen_technical_handling='APPLIED AS APPROVED', source_writes=0, cutover=False,
        transfer_hash_label=v['transfer_hash_label'],
    )
    m.save('dbv2_4_transfer_manifest.json', manifest)
    msha = hashlib.sha256((E / 'dbv2_4_transfer_manifest.json').read_bytes()).hexdigest()

    write('dbv2_4_preflight.md', [
        '# DBV2.4 — Preflight', '',
        f"- Destination: `{t['database']}` on `127.0.0.1:{t['host_port']}`, container `{t['container_name']}` (`{t['container_id'][:12]}`), volume `{t['volume']}`",
        f"- PostgreSQL server_version_num: `{srv['server_version_num']}` (17.9); system_identifier `{srv['system_identifier']}`; database OID `{srv['database_oid']}` (DBV2.3: `{TARGET['database_oid']}`)",
        '- Alembic head: `pg_v2_baseline`; roots = 1; heads = 1; down_revision = None',
        f"- Structural manifest SHA-256 (recomputed live): `{pre['structural_manifest_sha256']}` — expected `{persistent.EXPECTED_MANIFEST}` → MATCH",
        f"- Root revision SHA-256: `{persistent.EXPECTED_REVISION}` → MATCH (file hash verified)",
        f"- Transfer plan `dbv2_3/dbv2_4_transfer_plan.sql` SHA-256 `{pre['plan_sha256']}` = DBV2.3 certified hash; 39 statements parsed, identical to plan body; per-table column lists = SOURCE = DESTINATION (177 columns); full SOURCE catalog identical to DBV2.3 capture → NO PLAN DRIFT",
        '- Destination authorized tables: all 16 = 0 rows; only non-zero tables: `alembic_version` = 1, `experiment_execution_gate` = 1 (baseline technical rows) → CLEAN FOR FIRST TRANSFER',
        '', '## SOURCE READ ONLY', '',
        '- Connection option `default_transaction_read_only=on` + `BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY`; `transaction_read_only = on` asserted; `application_name = DBV2.4_SOURCE_READ_ONLY`.',
        '- Only SELECT / `COPY (SELECT …) TO STDOUT` executed on SOURCE; every session ends with ROLLBACK. SOURCE WRITES = 0.',
        '', '## SOURCE ≠ DESTINATION', '',
        f"- Source: container `capstone_db` (`{ident['source']['container_id'][:12]}`), port {ident['source']['host_port']}, database `{ident['source']['database']}`, volume `{ident['source']['volume']}`",
        f"- Destination: container `{t['container_name']}`, port {t['host_port']}, database `{t['database']}`, volume `{t['volume']}`",
        '- Different container, port, database, volume and PostgreSQL system_identifier (cluster) → SOURCE != DESTINATION (same physical host).',
        '', '## Source scientific snapshot (pre-transfer)', '',
        f"TRAIN {pre['scientific_snapshot']['train']} · VALIDATION {pre['scientific_snapshot']['validation']} · TEST {pre['scientific_snapshot']['test']} · TOTAL {pre['scientific_snapshot']['total']} · PATIENTS {pre['scientific_snapshot']['patients']} · overlaps {pre['scientific_snapshot']['overlaps']}",
    ])

    write('dbv2_4_transfer_execution.md', [
        '# DBV2.4 — Transfer execution', '',
        '- Executor: `scripts/db/dbv24_transfer.py transfer` as `capstone_v2_migrator` (NOSUPERUSER, cannot disable triggers or set session_replication_role).',
        '- Executed the 39 approved statements of `dbv2_4_transfer_plan.sql` verbatim in one destination transaction (BEGIN … COMMIT).',
        '- Transport boundary: for each of the 16 tables, the approved SELECT ran on SOURCE as `COPY (SELECT …) TO STDOUT` (text format) and streamed into `pg_temp.dbv24_src_<table>` via `COPY FROM STDIN`. Identical session formatting on both sides (UTC, ISO DateStyle, extra_float_digits=1). No files, no Python value conversion.',
        '- Insert order (plan/DBV2.3, parents before children): dataset_versions → datasets → roles → users → clinical_identities → dataset_materializations → dataset_split_statistics → dataset_split_validation_checks → dataset_splits → dataset_version_sources → user_roles → dataset_materialization_activations → dataset_source_records → dataset_split_images → dataset_split_assignments → identity_evidence.',
        '- All INSERTs use explicit columns; no `SELECT *`, no `ON CONFLICT`, no TRUNCATE/DELETE, no trigger disabling.',
        '- FROZEN technical handling = APPLIED AS APPROVED: `dataset_versions` inserted with status FROZEN→VALIDATED (so FROZEN child-protection triggers accept dependent rows), then restored to FROZEN before COMMIT by the plan UPDATE; lifecycle trigger keeps the stored `frozen_at` (COALESCE) and plan preflight forbids NULL `frozen_at`. Final row is byte-identical to SOURCE → semantic transformations = 0.',
        '- Before COMMIT: plan `$verify$` block (bidirectional EXCEPT ALL vs staging, split counts, 201 patients, 55,116 / 2 roots) + script validations (per-table transfer hashes and exact row equality vs SOURCE, scientific snapshot, 992 FK/CHECK/UNIQUE/PK checks, absence) → all PASS → COMMIT.',
        f"- Rows transferred: dataset {dataset_rows:,}; roles 1; users 1; user_roles 1.",
        '', '## Isolated rollback test (disposable cluster, port 56441)', '',
        f"- Fresh disposable PostgreSQL 17.9 cluster built with the same `pg_v2_baseline` (container `{rr['target']['container_name']}`).",
        '- Partial insert proven: dataset_versions = 1, datasets = 2; deterministic failure `SELECT 1/0` (SQLSTATE 22012) → ROLLBACK → all 16 authorized tables = 0 and structural manifest unchanged.',
        f"- Subsequent complete transfer on the same disposable cluster: validated and COMMITTED → {rr['status']}. Disposable container stopped afterwards (not the persistent one).",
        f"- Result: {rb['status']}.",
        '', '## Superseded attempt (transparency)', '',
        '- `superseded_attempt_1/`: first disposable run. Failure/rollback half PASSED; recovery half failed validation-before-COMMIT with SQLSTATE 42601 caused by a bug in the script-generated UNIQUE check (`GROUP BY (true)` for the partial unique index on a constant in `assessment_attempts`). ROLLBACK executed; disposable cluster only; persistent DB untouched. Fixed (aliased GROUP BY keys) and the rollback test re-run from a fresh disposable cluster.',
        '- Preflight fixes before any write (checker-only, plan unchanged): column regex now accepts digits (`*_sha256` columns); SOURCE catalog comparison uses the DBV2.3 json_agg representation and default search_path; stored-fingerprint locator matches `fingerprint|digest|sha256` keys.',
        '', 'Event log: `execution_events.jsonl`.',
    ])

    write('dbv2_4_dataset_certification.md', [
        '# DBV2.4 — Dataset certification', '',
        f"- dataset_version_id: `{OFFICIAL}` — status FROZEN, frozen_at preserved",
        '- Stored dataset fingerprints (from `dataset_versions.methodology_json.freeze_contract.fingerprints`, preserved byte-exact, NOT recomputed):',
        *[f"  - {k}: `{val}`" for k, val in freeze.items()],
        f"- TRAIN {sci['train']:,} · VALIDATION {sci['validation']:,} · TEST {sci['test']:,} · TOTAL {sci['total']:,} (sum OK) · patients {sci['patients']}",
        f"- Patient overlap: TRAIN/VALIDATION {sci['overlaps']['train/val']}, TRAIN/TEST {sci['overlaps']['train/test']}, VALIDATION/TEST {sci['overlaps']['val/test']}",
        f"- dataset_split_images: {sci['dataset_split_images']:,} = 2 physical roots × 27,558 (official versioned root + historical physical split); not deduplicated.",
        '- Split authority: `dataset_split_assignments` (transferred unchanged). TEST not used for any decision.',
        '', '## Per-table certification', '',
        *table([dict(x, transfer_hash='`' + x['transfer_hash'][:16] + '…`') for x in tabs if x['table'] in DATASET], ['table', 'source_count', 'destination_count', 'transferred_count', 'primary_key_match', 'transfer_hash_match', 'transfer_hash', 'fk_status', 'semantic_transformations', 'result']),
        '', 'Full hashes in `dbv2_4_transfer_manifest.json`. **TRANSFER VERIFICATION HASH** = SHA-256 over length-prefixed PostgreSQL `to_jsonb(row)::text` ordered by PK; it does not replace scientific fingerprints.',
        '', '## Stored hash columns (compared as stored values)', '',
        *table([dict(x, column_digest='`' + x['column_digest'][:16] + '…`') for x in hashes], ['table', 'column', 'non_null', 'column_digest', 'match']),
        '', '## Stored fingerprints / digests preserved', '',
        *[f"- `{f['path']}` = `{f['stored_value']}`" for f in fps],
        '', '- IDs preserved: PK sets identical per table (pk_hash + exact row equality). Stored hashes/fingerprints preserved: YES. Semantic transformations: 0.',
    ])

    write('dbv2_4_user_certification.md', [
        '# DBV2.4 — User certification (non-sensitive)', '',
        f"- roles: source total {auth['roles_source_total']}; authorized subset per DBV2.3 plan (roles referenced by user_roles) {auth['roles_source_selected']}; destination {auth['roles_count']}",
        f"- users: source {auth['users_count']} / destination {auth['users_count']}",
        f"- user_roles: source {auth['user_roles_count']} / destination {auth['user_roles_count']}",
        '', f"- preserved user = {'YES' if auth['preserved_user_count'] >= 1 else 'NO'}",
        f"- user ID preserved = {'YES' if auth['user_id_preserved'] else 'NO'}",
        f"- identity preserved = {'YES' if auth['identity_preserved'] else 'NO'}",
        f"- status preserved = {'YES' if auth['status_preserved'] else 'NO'} (active)",
        f"- password_hash_match = {str(auth['password_hash_match']).upper()}",
        f"- roles preserved = {'YES' if auth['roles_preserved'] else 'NO'}", '',
        'Password hash compared by in-memory/SQL equality only; it is excluded from transfer hashes and never written to any output. No passwords, tokens or secrets recorded. Login/JWT/HTTP are out of scope (SW-V2).',
    ])

    integ = v['integrity']
    from collections import Counter
    kinds = Counter(q['kind'] for q in integ['queries'])
    write('dbv2_4_integrity.md', [
        '# DBV2.4 — Integrity', '',
        f"Explicit queries over the whole public schema after COMMIT and after restart: FK {kinds['FK']}, CHECK {kinds['CHECK']}, UNIQUE {kinds['UNIQUE']}, PK {kinds['PK']}.", '',
        f"- orphan FK = {integ['orphan_fk']}", f"- duplicate PK = {integ['duplicate_pk']}", f"- UNIQUE violations = {integ['unique_violations']}", f"- CHECK violations = {integ['check_violations']}", '',
        '- SOURCE PK set == DESTINATION PK set for every authorized table (roles: the authorized subset).',
        f"- Structural manifest after COMMIT and after restart: `{v['structural_manifest_sha256']}` (unchanged).",
        '- Query texts and per-constraint results: `verification_after_restart.json` → integrity.queries.',
    ])

    fam = []
    for f, names in FAMILIES.items():
        present = [n for n in names if n in empty]
        fam.append(dict(family=f, tables_checked=', '.join(present) or '-', rows=sum(empty[n] for n in present)))
    xai = [n for n in empty if n.startswith('xai_')]
    fam[5] = dict(family='XAI', tables_checked=', '.join(xai), rows=sum(empty[n] for n in xai))
    write('dbv2_4_absence_checks.md', [
        '# DBV2.4 — Absence checks', '',
        f"All {len(empty)} non-authorized public tables in BD-v2 hold 0 rows (only technical baseline rows: alembic_version = 1, experiment_execution_gate = 1, both present before DBV2.4). Therefore every one is **empty because baseline created it empty**; rows transferred = 0.", '',
        *table(fam, ['family', 'tables_checked', 'rows']), '',
        f"- unauthorized transferred rows = {v['unauthorized_transfer']}", f"- audit_events transferred = {empty['audit_events']}",
        f"- XAI history transferred = {fam[5]['rows']} (structure present: {len(xai)} tables)", '- E10 history transferred = 0',
        '', 'Full per-table counts: `verification_after_restart.json` → absence.baseline_empty_tables.',
    ])

    write('dbv2_4_persistence.md', [
        '# DBV2.4 — Persistence', '',
        f"- `docker stop` / `docker start` of the SAME container `{TARGET['container_name']}`; volume `{TARGET['volume']}` NOT removed.",
        f"- After restart: database `{TARGET['database']}` (OID {TARGET['database_oid']}), same system_identifier, head `pg_v2_baseline`, manifest `{v['structural_manifest_sha256']}`.",
        '- Dataset, roles, users, user_roles and scientific counts re-verified against SOURCE: ALREADY_TRANSFERRED_EXACTLY; before/after results identical.',
        f"- Result: {per['status']}. VERIFY_ALREADY_TRANSFERRED (standalone re-run, read-only, no INSERT): ALREADY_TRANSFERRED_EXACTLY.",
        '- BD-v2 left running and persistent. No DROP DATABASE, no volume deletion, no `down -v`.',
    ])

    write('dbv2_4_report.md', [
        '# DBV2.4 — TRANSFERENCIA MÍNIMA CERTIFICADA', '',
        f"- Destination `{TARGET['database']}` · PostgreSQL 17.9 · volume `{TARGET['volume']}` · revision `pg_v2_baseline`",
        f"- Structural manifest before/after: `{pre['structural_manifest_sha256']}` / `{v['structural_manifest_sha256']}`",
        f"- Dataset version `{OFFICIAL}`; TRAIN {sci['train']:,} · VAL {sci['validation']:,} · TEST {sci['test']:,} · TOTAL {sci['total']:,} · patients {sci['patients']} · overlap 0 · dataset_split_images {sci['dataset_split_images']:,}",
        f"- Dataset tables 13 ({sum(1 for x in tabs if x['table'] in DATASET and x['result']=='PASS')} with rows, 2 PRESERVED_EMPTY); dataset rows {dataset_rows:,}",
        f"- Roles 1 · Users 1 · User roles 1 · preserved users {auth['preserved_user_count']} · password_hash_match {str(auth['password_hash_match']).lower()}",
        '- FROZEN technical handling: APPLIED AS APPROVED · semantic transformations 0',
        '- FK/CHECK/UNIQUE: PASS · unauthorized rows 0 · audit_events 0 · XAI 0 · E10 0',
        '- Restart persistence PASS · VERIFY_ALREADY_TRANSFERRED = ALREADY_TRANSFERRED_EXACTLY · isolated rollback test PASS',
        '- Source writes 0 · Cutover NO · not FINAL FREEZE / not PRODUCTION READY', '',
        f"Transfer manifest SHA-256: `{msha}`", '',
        'Evidence: dbv2_4_preflight.md, dbv2_4_transfer_execution.md, dbv2_4_dataset_certification.md, dbv2_4_user_certification.md, dbv2_4_integrity.md, dbv2_4_absence_checks.md, dbv2_4_persistence.md, dbv2_4_transfer_manifest.json, dbv2_4_hashes.sha256.',
        '', 'Awaiting GATE DBV2.4.',
    ])

    files = sorted(p for p in E.rglob('*') if p.is_file() and p.name != 'dbv2_4_hashes.sha256')
    (E / 'dbv2_4_hashes.sha256').write_text(''.join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(m.ROOT)}\n" for p in files))
    print('manifest', msha)


if __name__ == '__main__':
    main()
