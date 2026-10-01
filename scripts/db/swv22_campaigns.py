"""SWV2.2: READ ONLY continuity evidence for campaign configuration over PostgreSQL v2.

entry    record the operational entry state (application logins after SWV2.1) before any SWV2.2 change.
check    SWV2.0/SWV2.1 continuity derivation (identity, structural manifest, baseline, dataset, fingerprints,
         users) allowing only: the recorded entry state, and the rows of an explicitly declared SWV2.2
         configuration-demonstration campaign (never executed). Every other row outside the transferred set
         still fails, including runs, sessions, attempts, records, evaluations and XAI.
runtime  inside capstone_backend: session role/flags and require_e10_schema (SWV2.1 probe).
smoke    unauthenticated infrastructure endpoints over real HTTP (SWV2.1 probe).

Never prints or stores passwords, password hashes, tokens or credentialed URLs.
"""
import argparse
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/db'))
import swv20_integration as swv20  # noqa: E402
import swv21_backend as swv21  # noqa: E402

E = ROOT / 'docs/audits/sw_v2/swv2_2'
ENTRY = E / 'swv2_2_entry_state.json'
CAMPAIGN_TABLES = ('experimental_campaigns', 'campaign_configurations', 'campaign_members')
# Written by swv22_api_probe.py (blank-name POST) before the validation-order fix in
# CampaignService.configure: a truthful, successful dataset verification with no campaign attached.
# audit_events is append-only, so it is attributed here field by field instead of being removed.
PROBE_EVIDENCE = dict(id='157491f3-0967-4a95-9be5-6cdcf7dd7e56', event_type='ml.dataset_verification',
                      action='verify', request_method='CLI', request_path='campaigns.configure', success=True,
                      resource_type='dataset_version', resource_id='d8c0cab5-09dd-597f-9de7-7ca01aee2ec2',
                      created_at='2026-10-01 01:33:14.056576+00')


def save(name, obj):
    E.mkdir(parents=True, exist_ok=True)
    (E / name).write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, default=str) + '\n')


def audit_rows(c):
    return [dict(r) for r in c.execute("""SELECT id::text, event_type, action, request_method, request_path, success,
        resource_type, resource_id, created_at::text FROM audit_events ORDER BY created_at, id""")]


def entry():
    with swv20.session(5432, 'malaria_experiments') as c:
        state = dict(
            users_last_login_at=swv20.scalar(c, 'SELECT last_login_at::text FROM users'),
            audit_events=audit_rows(c),
        )
        from dbv24_transfer import TABLES, all_counts
        state['counts'] = {t: n for t, n in all_counts(c).items() if t not in TABLES and n}
    assert all(r['event_type'] == 'USER_LOGIN_SUCCEEDED' and r['request_path'] == '/api/v1/auth/login'
               for r in state['audit_events']), 'UNEXPECTED_ENTRY_AUDIT_EVENT'
    assert state['counts'] == {'alembic_version': 1, 'experiment_execution_gate': 1,
                               'audit_events': len(state['audit_events'])}, state['counts']
    state['note'] = ('Application logins after SWV2.1 (normal login behaviour: users.last_login_at + '
                     'USER_LOGIN_SUCCEEDED). Not produced by SWV2.2.')
    save('swv2_2_entry_state.json', state)
    return state


def demo_rows(c, campaign_id):
    """Rows legitimately produced by saving the declared demonstration campaign through the API."""
    if campaign_id is None:
        return set(), {}
    members = {r['id'] for r in c.execute(
        'SELECT id::text FROM campaign_members WHERE campaign_id=%s', (campaign_id,))}
    camp = c.execute('SELECT dataset_evidence_id::text AS evidence, state, expected_count FROM experimental_campaigns '
                     'WHERE id=%s', (campaign_id,)).fetchone()
    assert camp and camp['state'] == 'frozen', 'DEMO_CAMPAIGN_NOT_FROZEN'
    assert len(members) == camp['expected_count'], 'DEMO_MEMBERS_INCOMPLETE'
    allowed = set()
    for r in c.execute("""SELECT id::text, event_type, resource_id, request_path, success, after_state
                          FROM audit_events""").fetchall():
        if r['id'] == camp['evidence']:
            assert r['event_type'] == 'ml.dataset_verification' and r['success'], 'DEMO_EVIDENCE_INVALID'
            assert r['request_path'] == 'campaigns.configure', r['request_path']
            allowed.add(r['id'])
        elif r['event_type'].startswith('ml.campaign.') and r['request_path'] == 'campaigns.e4' and (
                r['resource_id'] == campaign_id or r['resource_id'] in members):
            allowed.add(r['id'])
        elif r['event_type'] == 'ml.campaign.configured' and r['resource_id'] == campaign_id and r['success']:
            allowed.add(r['id'])
    return allowed, dict(campaign_id=campaign_id, members=len(members), expected_count=camp['expected_count'],
                         dataset_evidence_id=camp['evidence'])


def check(label, campaign_id=None):
    state = json.loads(ENTRY.read_text())
    swv20.save = lambda name, obj: save(name.replace('swv2_0_', 'swv2_2_'), obj)

    def users_hashes(c, t, original=swv20.hashes):
        if t != 'users':
            return original(c, t)
        current = swv20.scalar(c, 'SELECT last_login_at::text FROM users')
        assert current == state['users_last_login_at'], 'USERS_LAST_LOGIN_CHANGED_SINCE_SWV2_2_ENTRY'
        swv21.ENTRY_DELTA['users_last_login_at_entry'] = current
        return swv21.users_hashes(c, t, original)

    def absence(c):
        from dbv24_transfer import TABLES, all_counts
        allowed, demo = demo_rows(c, campaign_id)
        rows = audit_rows(c)
        entry_ids = {r['id'] for r in state['audit_events']}
        assert [r for r in rows if r['id'] in entry_ids] == state['audit_events'], 'ENTRY_AUDIT_EVENTS_CHANGED'
        extra = [r for r in rows if r['id'] not in entry_ids]
        probe = [r for r in extra if r['id'] == PROBE_EVIDENCE['id']]
        assert probe == [PROBE_EVIDENCE], 'PROBE_EVIDENCE_CHANGED'
        assert all(r['id'] in allowed for r in extra if r['id'] != PROBE_EVIDENCE['id']), 'UNATTRIBUTED_AUDIT_EVENTS'
        outside = {t: n for t, n in all_counts(c).items() if t not in TABLES}
        assert outside.pop('alembic_version') == 1 and outside.pop('experiment_execution_gate') == 1
        assert outside.pop('audit_events') == len(rows)
        campaign_rows = {t: outside.pop(t) for t in CAMPAIGN_TABLES}
        if campaign_id is None:
            assert not any(campaign_rows.values()), 'UNDECLARED_CAMPAIGN_ROWS'
        else:
            assert campaign_rows['experimental_campaigns'] == 1
            for t in ('campaign_configurations', 'campaign_members'):
                assert swv20.scalar(c, f'SELECT count(*) FROM {t} WHERE campaign_id<>%s', (campaign_id,)) == 0, t
        assert not any(outside.values()), 'UNAUTHORIZED_ROWS:' + ','.join(t for t, n in outside.items() if n)
        return dict(unauthorized_rows=0, technical_rows={'alembic_version': 1, 'experiment_execution_gate': 1},
                    entry_audit_events=len(entry_ids), swv2_2_audit_events=len(extra),
                    probe_dataset_evidence=PROBE_EVIDENCE['id'], campaign_rows=campaign_rows,
                    demonstration_campaign=demo or None, scientific_execution_rows=0,
                    empty_tables=sorted(t for t, n in outside.items() if not n))

    swv20.hashes = users_hashes
    swv20.absence = absence
    r = swv20.check(label, 5432, 'malaria_experiments', 'capstone_db', 'malaria_experiments')
    volume = [m['name'] for m in r['docker']['mounts'] if m['destination'] == '/var/lib/postgresql/data']
    assert volume == ['capstone_v2_isolated_persistent_data'], volume
    return r


def main():
    a = argparse.ArgumentParser()
    a.add_argument('action', choices=['entry', 'check', 'runtime', 'smoke'])
    a.add_argument('--label', default='final')
    a.add_argument('--demo-campaign-id')
    x = a.parse_args()
    swv21.save = lambda name, obj: save(name.replace('swv2_1_', 'swv2_2_'), obj)
    if x.action == 'entry':
        entry()
    elif x.action == 'check':
        check(x.label, x.demo_campaign_id)
    elif x.action == 'runtime':
        swv21.runtime(x.label)
    else:
        swv21.smoke(x.label)
    print(x.action.upper(), x.label, 'PASS')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        safe = dict(status='BLOCKED', error_type=type(error).__name__, sqlstate=getattr(error, 'sqlstate', None),
                    at=[f'{Path(f.filename).name}:{f.lineno}' for f in traceback.extract_tb(error.__traceback__)])
        if isinstance(error, (AssertionError, RuntimeError)) and error.args and isinstance(error.args[0], str):
            safe['invariant'] = error.args[0]
        save('blocked.json', safe)
        print(json.dumps(safe, default=str))
        sys.exit(1)
