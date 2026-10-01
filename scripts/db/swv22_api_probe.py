"""SWV2.2 real-HTTP probe of /api/campaigns inside capstone_backend (stdin to `python -`).

Token issued with the backend's own create_access_token for the existing active user (no login,
no password). Only negative/read-only calls: asserts that nothing is persisted. Never prints the token.
"""
import copy
import json
import urllib.error
import urllib.parse
import urllib.request

from sqlalchemy import text

from app.db import get_primary_engine
from app.security import create_access_token

BASE = 'http://127.0.0.1:8000'
DATASET = 'd8c0cab5-09dd-597f-9de7-7ca01aee2ec2'
TABLES = ('experimental_campaigns', 'campaign_configurations', 'campaign_members', 'campaign_attempts', 'runs',
          'train_execution_sessions', 'audit_events')


def counts():
    with get_primary_engine().connect() as c:
        return {t: c.execute(text(f'SELECT count(*) FROM {t}')).scalar_one() for t in TABLES}


with get_primary_engine().connect() as c:
    user = c.execute(text("""SELECT u.id::text, u.username, array_agg(r.name) roles FROM users u
        JOIN user_roles ur ON ur.user_id=u.id JOIN roles r ON r.id=ur.role_id WHERE u.status='active'
        GROUP BY u.id""")).mappings().one()
token = create_access_token(user['id'], user['username'], list(user['roles']))


def call(method, path, body=None, params=None):
    url = BASE + path + ('?' + urllib.parse.urlencode(params) if params else '')
    data = json.dumps(body).encode() if body is not None else None
    q = urllib.request.Request(url, data=data, method=method, headers={
        'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(q, timeout=120) as r:
            return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        raw = e.read() or b'{}'
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {'raw': raw.decode()[:200]}


def preview(cfg, dataset=DATASET):
    return call('GET', '/api/campaigns/preview', params={'configuration': json.dumps(cfg),
                                                         **({'dataset_version_id': dataset} if dataset else {})})


out = {}
before = counts()
s, catalog = call('GET', '/api/campaigns/catalog')
out['catalog'] = dict(status=s, models=[m['id'] for m in catalog['models']],
                      optimizers=[o['id'] for o in catalog['optimizers']], presets=[p['id'] for p in catalog['presets']],
                      protocol_template=catalog['protocol']['template_version'],
                      parameters={m['id']: {p['key']: dict(default=p['default'], editable=p['editable'])
                                            for p in m['parameters']} for m in catalog['models']})
s, datasets = call('GET', '/api/datasets', params={'datasource': 'malaria'})
out['datasets'] = dict(status=s, items=[{k: d[k] for k in ('dataset_version_id', 'status', 'trainable', 'train_records',
                                                             'val_records', 'test_records', 'source_record_count',
                                                             'patient_count')} for d in datasets['items']])
default = copy.deepcopy(next(p for p in catalog['presets'] if p['id'] == catalog['default_preset'])['configuration'])
e7 = copy.deepcopy(next(p for p in catalog['presets'] if p['id'] == 'capstone_science_e7_v1')['configuration'])
for name, cfg in (('default_preset', default), ('approved_plan_preset', e7)):
    s, body = preview(cfg)
    out['preview_' + name] = dict(status=s, valid=body['valid'], summary={k: v for k, v in body['summary'].items()
                                                                         if k != 'configuration_list'},
                                  protocol_version=body['protocol']['version'],
                                  checks={c['check']: c['status'] for c in body['checks']})
bad = copy.deepcopy(default)
bad['variants'][0]['parameters']['vgg16']['max_epochs'] = 0
s, body = preview(bad)
out['preview_invalid_epochs'] = dict(status=s, valid=body['valid'], errors=body['errors'])
bad = copy.deepcopy(default)
bad['optimizers'] = ['adam', 'rmsprop']
s, body = preview(bad)
out['preview_invalid_optimizer'] = dict(status=s, valid=body['valid'], errors=body['errors'])
bad = copy.deepcopy(default)
bad['protocol']['early_stopping']['patience'] = -1
s, body = preview(bad)
out['preview_invalid_early_stopping'] = dict(status=s, valid=body['valid'], errors=body['errors'])
s, body = preview(default, dataset='00000000-0000-4000-8000-000000000001')
out['preview_unknown_dataset'] = dict(status=s, valid=body['valid'], dataset_check=body['checks'][0])
payload = dict(campaign_id='00000000-0000-4000-8000-0000000000aa', name='probe', purpose='probe',
               dataset_version_id=DATASET, configuration=copy.deepcopy(default))
s, body = call('POST', '/api/campaigns', {**payload, 'start': True})
out['post_extra_field'] = dict(status=s)
bad = copy.deepcopy(payload)
bad['configuration']['variants'][0]['parameters']['custom_cnn']['dropout'] = 1.5
s, body = call('POST', '/api/campaigns', bad)
out['post_invalid_parameter'] = dict(status=s, code=body.get('error', {}).get('details', {}).get('code'))
s, body = call('POST', '/api/campaigns', {**payload, 'name': '   '})
out['post_blank_name'] = dict(status=s, code=body.get('error', {}).get('details', {}).get('code'))
for method, path in (('POST', '/api/campaigns/00000000-0000-4000-8000-0000000000aa/execute'),
                     ('POST', '/api/campaigns/00000000-0000-4000-8000-0000000000aa/start'),
                     ('GET', '/api/campaigns/00000000-0000-4000-8000-0000000000aa')):
    out[f'{method} {path}'] = call(method, path)[0]
after = counts()
out['counts_before'], out['counts_after'] = before, after
out['persistent_writes'] = {t: after[t] - before[t] for t in TABLES}
print(json.dumps(out, default=str))
