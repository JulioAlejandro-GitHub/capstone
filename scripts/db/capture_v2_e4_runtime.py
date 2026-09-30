"""Capture the certified candidate's read-only runtime admission contract."""
import hashlib
import json
from probe_v2_e4_contract import E,ROOT,connect,guard


def main():
    t=guard()
    from v2_catalog_probe import snapshot
    with connect(t) as c:
        assert snapshot(c)==json.loads((E/'installed_catalog.json').read_text())
        functions={r['proname']:r['hash'] for r in c.execute("""SELECT p.proname, md5(pg_get_functiondef(p.oid)) hash
            FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname='public' AND (p.proname LIKE 'v2_%' OR p.proname LIKE 'e04_%')""").fetchall()}
        triggers=c.execute("""SELECT r.relname AS relation,t.tgname AS name,pg_get_triggerdef(t.oid) AS definition,
            t.tgenabled,t.tgdeferrable,t.tginitdeferred FROM pg_trigger t JOIN pg_class r ON r.oid=t.tgrelid
            JOIN pg_namespace n ON n.oid=r.relnamespace WHERE n.nspname='public'
            AND (t.tgname LIKE 'v2_%' OR t.tgname LIKE 'e04_%') ORDER BY t.tgname""").fetchall()
        constraints=c.execute("""SELECT conname AS name,pg_get_constraintdef(oid) AS definition,
            condeferrable,condeferred,convalidated FROM pg_constraint
            WHERE conrelid='public.evaluations'::regclass ORDER BY conname""").fetchall()
        indexes=c.execute("""SELECT c.relname AS name,pg_get_indexdef(i.indexrelid) AS definition,
            i.indisvalid,i.indisready,i.indisunique,i.indnullsnotdistinct FROM pg_index i
            JOIN pg_class c ON c.oid=i.indexrelid WHERE i.indrelid='public.evaluations'::regclass
            AND c.relname LIKE 'uq_e04_%' ORDER BY c.relname""").fetchall()
    contract=dict(stage='E10.10.5E.4',functions=functions,triggers=triggers,
                  evaluation_constraints=constraints,calibration_indexes=indexes)
    path=ROOT/'malaria_dl_local_project/src/malaria_dl/persistence/v2_runtime_contract.json'
    path.write_text(json.dumps(contract,indent=2)+'\n')
    (E/'runtime_contract_capture.json').write_text(json.dumps(dict(passed=True,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),functions=len(functions),triggers=len(triggers),
        constraints=len(constraints),indexes=len(indexes)),indent=2)+'\n')
    print('E.4 runtime admission contract captured')


if __name__=='__main__':main()
