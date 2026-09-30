"""DBV2.1 offline structural validator and review-catalog renderer.
Only reads SQL/files; never connects, executes SQL, imports an installer or application.
Requires pglast==8.4 (parser grammar 18.4; target server 17.9 is NOT certified).
"""
from __future__ import annotations
import argparse, collections, csv, hashlib, io, json, re
from pathlib import Path
from pglast import ast, parse_sql, parser, get_postgresql_version
from pglast.enums import ConstrType as CT
from pglast.stream import RawStream
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/audits/db_v2"
SQL = OUT / "dbv2_1_target_schema.sql"
def render(node):
    return RawStream()(node)
def norm(value):
    if isinstance(value, ast.Node):
        value = value()
    if isinstance(value, dict):
        return {
            k: norm(v)
            for k, v in value.items()
            if k
            not in (
                "location",
                "stmt_location",
                "stmt_len",
                "list_start",
                "list_end",
                "rexpr_list_start",
                "rexpr_list_end",
                "funcformat",
            )
        }
    if isinstance(value, (list, tuple)):
        return [norm(v) for v in value]
    return value


def strings(nodes):
    return tuple(n.sval for n in nodes or ())


def walk(value):
    if isinstance(value, ast.Node):
        value = value()
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from walk(v)
    elif isinstance(value, (tuple, list)):
        for v in value:
            yield from walk(v)


def catalogue(statements):
    tables, keys, functions, views, triggers, constraints, indexes = (
        {},
        collections.defaultdict(set),
        {},
        {},
        {},
        {},
        {},
    )
    primary = {}
    sequence = set()
    counts = collections.Counter()
    plpgsql = 0
    for sql in statements:
        parsed = parse_sql(sql)
        assert len(parsed) == 1, "One statement per resource entry required"
        s = parsed[0].stmt
        counts[type(s).__name__] += 1
        assert not isinstance(
            s,
            (
                ast.DropStmt,
                ast.TruncateStmt,
                ast.DeleteStmt,
                ast.UpdateStmt,
                ast.TransactionStmt,
            ),
        )
        if isinstance(s, ast.CreateStmt):
            t = s.relation.relname
            assert t not in tables and t != "alembic_version"
            assert not s.if_not_exists
            tables[t] = {c.colname: c for c in s.tableElts}
            assert len(tables[t]) == len(s.tableElts)
            assert all(isinstance(c, ast.ColumnDef) for c in s.tableElts)
            for column in s.tableElts:
                for co in column.constraints or ():
                    if co.contype == CT.CONSTR_IDENTITY:
                        assert (t, column.colname, co.generated_when) == (
                            "experiment_execution_events",
                            "id",
                            "a",
                        )
                        sequence.add("experiment_execution_events_id_seq")
                assert all(
                    co.contype
                    in (
                        CT.CONSTR_NOTNULL,
                        CT.CONSTR_NULL,
                        CT.CONSTR_DEFAULT,
                        CT.CONSTR_GENERATED,
                        CT.CONSTR_IDENTITY,
                    )
                    for co in column.constraints or ()
                ), ("Unextracted column constraint", t, column.colname)
        elif isinstance(s, ast.CreateSeqStmt):
            assert s.sequence.relname not in sequence
            sequence.add(s.sequence.relname)
        elif isinstance(s, ast.CreateFunctionStmt):
            name = ".".join(strings(s.funcname))
            assert name not in functions
            functions[name] = s
            options = {o.defname: o for o in s.options}
            if options["language"].arg.sval == "plpgsql":
                parser.parse_plpgsql_json(sql)
                plpgsql += 1
            body = options["as"].arg[0].sval
            # %ROWTYPE references must exist at function creation with checks ON.
            for t in re.findall(r"(?:public\.)?(\w+)%ROWTYPE", body, re.IGNORECASE):
                assert t in tables, ("Missing row type", name, t)
            if options["language"].arg.sval == "sql":
                parse_sql(body)
        elif isinstance(s, ast.AlterTableStmt):
            t = s.relation.relname
            assert t in tables, ("Unknown ALTER table", t)
            for cmd in s.cmds:
                c = cmd.def_
                assert isinstance(c, ast.Constraint), (
                    "Final shapes must precede constraints/views"
                )
                ident = (t, c.conname)
                assert ident not in constraints
                constraints[ident] = c
                if c.contype in (CT.CONSTR_PRIMARY, CT.CONSTR_UNIQUE):
                    cols = strings(c.keys)
                    assert set(cols) <= tables[t].keys()
                    keys[t].add(cols)
                    if c.contype == CT.CONSTR_PRIMARY:
                        assert t not in primary
                        primary[t] = cols
                elif c.contype == CT.CONSTR_FOREIGN:
                    parent = c.pktable.relname
                    assert parent in tables, ("Missing FK parent", ident, parent)
                    assert set(strings(c.fk_attrs)) <= tables[t].keys()
                    pc = strings(c.pk_attrs) or primary.get(parent)
                    assert pc and set(pc) <= tables[parent].keys()
                    assert pc in keys[parent], (
                        "FK target not unique before creation",
                        ident,
                        parent,
                        pc,
                    )
                    assert not c.skip_validation, ("Unvalidated FK", ident)
                elif c.contype == CT.CONSTR_CHECK:
                    assert not c.skip_validation
                    for node in walk(c.raw_expr):
                        if node.get("@") == "ColumnRef":
                            fields = node["fields"]
                            assert fields[0]["sval"] in tables[t], (
                                "Unknown CHECK column",
                                ident,
                                fields,
                            )
                else:
                    raise AssertionError(("Unreviewed constraint", ident, c.contype))
        elif isinstance(s, ast.IndexStmt):
            assert s.relation.relname in tables
            assert not s.concurrent and not s.if_not_exists
            assert s.idxname not in indexes
            indexes[s.idxname] = s
            for item in s.indexParams:
                if item.name:
                    assert item.name in tables[s.relation.relname]
            if (
                s.unique
                and s.whereClause is None
                and all(i.name for i in s.indexParams)
            ):
                keys[s.relation.relname].add(tuple(i.name for i in s.indexParams))
        elif isinstance(s, ast.ViewStmt):
            name = s.view.relname
            assert name not in views and name not in tables
            ctes = {
                n["ctename"] for n in walk(s.query) if n.get("@") == "CommonTableExpr"
            }
            for n in walk(s.query):
                if n.get("@") == "RangeVar":
                    assert n["relname"] in tables.keys() | views.keys() | ctes, (
                        "View dependency",
                        name,
                        n["relname"],
                    )
            views[name] = s
        elif isinstance(s, ast.CreateTrigStmt):
            name = (s.relation.relname, s.trigname)
            assert name not in triggers and s.relation.relname in tables
            fn = ".".join(strings(s.funcname))
            assert (fn if "." in fn else "public." + fn) in functions
            assert not s.trigname.startswith("RI_ConstraintTrigger")
            triggers[name] = s
        elif isinstance(s, ast.InsertStmt):
            assert s.relation.relname == "experiment_execution_gate", (
                "Scientific seed forbidden"
            )
    assert set(primary) == set(tables)
    return {
        "tables": tables,
        "functions": functions,
        "views": views,
        "triggers": triggers,
        "constraints": constraints,
        "indexes": indexes,
        "primary": primary,
        "sequence": sequence,
        "statements": counts,
        "plpgsql": plpgsql,
    }


DOMAINS = {
 'users':'A. Usuarios / seguridad','roles':'A. Usuarios / seguridad','user_roles':'A. Usuarios / seguridad',
 'models':'D. Modelos','model_versions':'E. Model versions / checkpoints','artifacts':'E. Model versions / checkpoints',
 'experiments':'F. Experimentos','runs':'G. Runs','run_configurations':'H. Run configurations',
 'run_threshold_calibration':'M. Calibración','run_checkpoint_policy':'E. Model versions / checkpoints',
 'run_clinical_metrics':'L. Métricas clínicas','run_metrics':'L. Métricas clínicas','training_history':'J. TRAIN / execution ledger',
 'evaluation_ensemble_members':'N. Ensembles','evaluations':'K. Evaluaciones',
 'schema_migrations':'Q. Auditoría y trazabilidad técnica','model_governance_backfill_audit':'Q. Auditoría y trazabilidad técnica',
 'confusion_matrices':'L. Métricas clínicas','classification_reports':'L. Métricas clínicas',
}
NEW_PURPOSE = {
 'xai_method_configurations':'Identidad reutilizable de método, implementación, versión y parámetros XAI.',
 'xai_region_attributions':'Atribución por región discreta; los mapas densos permanecen en archivos externos.',
 'xai_evaluation_protocols':'Identidad reproducible del protocolo de una métrica XAI extensible.',
 'xai_evaluation_members':'Miembros N:M de cada medición XAI, con rol y membresía congelada.',
 'xai_evidence':'Explicación individual reproducible con contexto experimental o celular y checkpoint.',
 'xai_artifacts':'Manifiesto de archivos numéricos y visuales externos de una explicación.',
 'xai_quantitative_evaluations':'Una medición vertical por protocolo y conjunto de explicaciones; NULL con razón.',
 'xai_interpretations':'Interpretación escrita y versionada de la explicación por un autor.',
 'xai_specialist_reviews':'Revisión clínica de la interpretación, independiente de Agreement.',
 'run_configurations':'Configuración científica efectiva, tipada e inmutable de cada TRAIN.',
 'evaluations':'Contexto científico, población, umbral y procedencia de una evaluación.',
 'evaluation_ensemble_members':'Componentes y pesos del ensemble de una evaluación.',
}

def domain(t):
    if t in DOMAINS: return DOMAINS[t]
    if t.startswith(('xai_', 'explainability_', 'cell_explanations')): return 'O. XAI'
    if t.startswith(('dataset_', 'datasets', 'clinical_identities', 'identity_evidence')): return 'B. Dataset'
    if t.startswith(('campaign_', 'experimental_campaigns')): return 'I. Campañas'
    if t.startswith(('train_', 'experiment_execution', 'local_execution')): return 'J. TRAIN / execution ledger'
    if t.startswith('assessment_'): return 'K. Evaluaciones'
    if t.startswith(('stage2_', 'deployed_', 'run_model_')): return 'P. Publicación / deployment'
    if t in {'execution_logs','errors','environment_packages','run_io_records','run_lineage','audit_events'}: return 'Q. Auditoría y trazabilidad técnica'
    return 'C. Imágenes / pacientes / splits'


def read_sql(path):
    source=path.read_text()
    return [source[r.stmt_location:r.stmt_location+r.stmt_len] if r.stmt_len else source[r.stmt_location:] for r in parse_sql(source)]


def signature_by_table(statements):
    result=collections.defaultdict(list)
    for sql in statements:
        s=parse_sql(sql)[0].stmt
        rel=getattr(s,'relation',None)
        if rel is not None: result[rel.relname].append(norm(s))
    return result


def table_constraints(c,t):
    return [(name,co) for (table,name),co in c['constraints'].items() if table==t]


def colrefs(expr):
    return {n['fields'][0]['sval'] for n in walk(expr) if n.get('@')=='ColumnRef'}


def constraint_columns(co):
    if co.contype==CT.CONSTR_FOREIGN: return strings(co.fk_attrs)
    if co.contype==CT.CONSTR_CHECK: return colrefs(co.raw_expr)
    return strings(co.keys)


def fk_rule(code):
    return {'a':'NO ACTION','r':'RESTRICT','c':'CASCADE','n':'SET NULL','d':'SET DEFAULT'}[code]


def constraint_sql(t,name,co):
    return 'ALTER TABLE public.'+t+' ADD CONSTRAINT '+name+' '+render(co)+';'


def classification(name):
    if name in {'prevent_model_governance_audit_mutation'}: return 'LEGACY_REDUNDANT'
    if name.startswith(('assessment_canonical','assessment_structural_hash','campaign_json_','campaign_environment_identity','dbv21_xai_configuration')): return 'TECHNICAL'
    return 'REQUIRED_DB_INVARIANT'


def write_or_compare(path,content,write):
    if write: path.write_text(content)
    else: assert path.read_text()==content, f'Derived artifact drift: {path}'


def csv_text(fields,rows):
    buff=io.StringIO(newline=''); w=csv.DictWriter(buff,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(rows); return buff.getvalue()


def build(write=False):
    statements=read_sql(SQL); c=catalogue(statements); source=SQL.read_text()
    assert source.startswith('-- DBV2.1 STRUCTURAL SPECIFICATION\n-- DESIGN ARTIFACT ONLY\n-- DO NOT EXECUTE\n-- NOT AN ALEMBIC MIGRATION\n')
    oldstatements=[]
    for p in sorted((ROOT/'alembic_v2/baseline').glob('*.sql')):
        if not p.name.startswith(('10_','11_')): oldstatements += read_sql(p)
    old_by_table=signature_by_table(oldstatements); new_by_table=signature_by_table(statements)
    oldtables={s.stmt.relation.relname for sql in oldstatements for s in parse_sql(sql) if isinstance(s.stmt,ast.CreateStmt)}
    old_matrix={r['Objeto futuro']:r for r in csv.DictReader((ROOT/'docs/audits/e10_10_4_schema_matrix.csv').open())}
    purposes={t:NEW_PURPOSE.get(t,old_matrix.get(t,{}).get('Responsabilidad','Entidad persistente de '+domain(t))) for t in oldtables|c['tables'].keys()}
    matrix=[]
    for t in sorted(oldtables|c['tables'].keys()|{'confusion_matrices','classification_reports'}):
        if t in {'confusion_matrices','classification_reports'}:
            action='VIEW'; reason='Lectura derivada de run_clinical_metrics; evita duplicar conteos y tasas.'
            purpose='Proyección derivada de métricas clínicas.'
        elif t not in c['tables']:
            action='REMOVE'; reason='Historia de instalación/backfill legacy no necesaria para construir una base vacía; conservar fuera de BD-v2.'; purpose=purposes[t]
        elif t not in oldtables:
            action='NEW'; reason='No existe entidad equivalente; separa identidad/configuración o relación N:M sin duplicar explicaciones.'; purpose=purposes[t]
        else:
            action='KEEP' if old_by_table[t]==new_by_table[t] else 'MODIFY'
            reason=('Contrato existente representa este concepto y sus dependencias; no requiere otra entidad.' if action=='KEEP' else 'Ajuste explícito de dominio recall, normalización XAI, índices o protección referencial; detalle SQL y ficha.')
            purpose=purposes[t]
        matrix.append(dict(domain=domain(t),table=t,action=action,purpose=purpose,justification=reason))
    write_or_compare(OUT/'dbv2_1_table_matrix.csv',csv_text(['domain','table','action','purpose','justification'],matrix),write)
    columns=[]; relationships=[]; detail=[]; er=['# DBV2.1 — ER completo','', '104 tablas de aplicación. Alembic administrará su ledger técnico por separado. Cada arista es una FK; relaciones N:M se detallan en el CSV.','', '```mermaid','erDiagram']
    for t,cols in sorted(c['tables'].items()):
        cons=table_constraints(c,t)
        keys=[strings(co.keys) for _,co in cons if co.contype in (CT.CONSTR_PRIMARY,CT.CONSTR_UNIQUE)]
        indices=[(n,s) for n,s in c['indexes'].items() if s.relation.relname==t]
        for _,idx in indices:
            if idx.unique and idx.whereClause is None and all(x.name for x in idx.indexParams): keys.append(tuple(x.name for x in idx.indexParams))
        detail += ['## '+t,'',purposes[t],'','Dominio: '+domain(t)+'. Acción: '+next(r['action'] for r in matrix if r['table']==t)+'.','', 'Columnas (PK implica NOT NULL; GENERATED no es un DEFAULT):','', '| Columna | Tipo PostgreSQL | NULL | DEFAULT / generación |','|---|---|---|---|']
        er += [f'    {t} {{']+[f'        {render(col.typeName).replace(" ","_").replace(",","_").replace("(","_").replace(")","")} {name}'+(' PK' if name in c['primary'][t] else '') for name,col in cols.items() if name in c['primary'][t]]+['    }']
        for name,col in cols.items():
            default=''; nullable=name not in c['primary'][t]
            for co in col.constraints or ():
                if co.contype==CT.CONSTR_NOTNULL: nullable=False
                if co.contype==CT.CONSTR_DEFAULT: default=render(co.raw_expr)
                if co.contype in (CT.CONSTR_GENERATED,CT.CONSTR_IDENTITY): default=render(co)
            attached=[(n,co) for n,co in cons if name in constraint_columns(co)]
            fk=' | '.join(n+': '+render(co) for n,co in attached if co.contype==CT.CONSTR_FOREIGN)
            uniq=' | '.join(n+': '+render(co) for n,co in attached if co.contype==CT.CONSTR_UNIQUE)
            uniq += (' | ' if uniq else '') + ' | '.join(n+': '+render(idx) for n,idx in indices if idx.unique and any(x.name==name for x in idx.indexParams))
            chk=' | '.join(n+': '+render(co) for n,co in attached if co.contype==CT.CONSTR_CHECK)
            desc='Campo '+name+' de '+t+'.'
            if 'jsonb' in render(col.typeName): desc+=' Snapshot, parámetros extensibles o metadatos variables; no sustituye las FK ni columnas tipadas. Canonical/hash preserva los bytes de origen cuando aplica.'
            if any(x in name for x in ('sha256','hash')): desc+=' Identidad/procedencia; conservar valor y representación canónica original, sin recalcular al transferir.'
            if name.endswith('_at'): desc+=' Auditoría temporal del evento indicado; sin actualización automática salvo trigger explícito.'
            if name=='clinical_target_recall': desc='Objetivo científico efectivo del TRAIN; numeric NOT NULL, 0 < valor <= 1, sin default. El software selecciona el valor.'
            columns.append(dict(table=t,column=name,postgres_type=render(col.typeName),nullable='YES' if nullable else 'NO',default=default,PK='YES' if name in c['primary'][t] else '',FK=fk,UNIQUE=uniq.strip(' |'),CHECK=chk,description=desc))
            detail.append('| '+name+' | '+render(col.typeName)+' | '+('YES' if nullable else 'NO')+' | '+default.replace('|','\\|')+' |')
        detail += ['', 'Restricciones exactas (FK incluye ON DELETE; ON UPDATE omitido significa NO ACTION):','', '```sql']+[constraint_sql(t,n,co) for n,co in cons]+['```','', 'Índices explícitos: '+(', '.join('`'+n+'`' for n,_ in indices) or 'ninguno adicional a PK/UNIQUE')+'.', 'Auditoría: '+(', '.join(n for n in cols if n.endswith('_at') or n in {'created_by','updated_by','actor_user_id'}) or 'heredada de su padre y registrada en la relación')+'.', 'JSONB: '+(', '.join(n for n,v in cols.items() if 'jsonb' in render(v.typeName)) or 'no utiliza')+'. Sus usos se describen por columna en el CSV; snapshots no son otra entidad ni autoridad alternativa.', 'Provenance/hash: '+(', '.join(n for n in cols if any(x in n for x in ('hash','sha256','canonical','source_','provenance'))) or 'por FK a las entidades de origen')+'.','']
        for n,co in cons:
            if co.contype!=CT.CONSTR_FOREIGN: continue
            cc=strings(co.fk_attrs); parent=co.pktable.relname; pc=strings(co.pk_attrs) or c['primary'][parent]
            one=any(set(k)<=set(cc) for k in keys); card='1:1' if one else '1:N'
            optional=any(next(x for x in columns if x['table']==t and x['column']==xcol)['nullable']=='YES' for xcol in cc)
            relationships.append(dict(relationship='FK',name=n,parent_table=parent,parent_columns=','.join(pc),child_table=t,child_columns=','.join(cc),cardinality=card,optional=str(optional).lower(),on_delete=fk_rule(co.fk_del_action),on_update=fk_rule(co.fk_upd_action),deferrable=str(co.deferrable).lower(),initially_deferred=str(co.initdeferred).lower(),via=''))
            er.append(f'    {parent} '+('o|' if optional else '||')+('..o| ' if one else '..o{ ')+t+f' : "{n}"')
    # Semantic N:M paths in addition to every physical FK.
    bridges={
      'user_roles':('users','roles'),'dataset_version_sources':('dataset_versions','datasets'),
      'dataset_split_assignments':('dataset_versions','dataset_source_records'),
      'evaluation_ensemble_members':('evaluations','model_versions'),
      'xai_evaluation_members':('xai_quantitative_evaluations','xai_evidence'),
      'run_dataset_images':('runs','dataset_split_images'),'run_model_deployments':('runs','deployed_model_versions'),
      'scientific_validation_images':('scientific_validation_sessions','microscopy_images'),
      'scientific_validation_detection_runs':('scientific_validation_sessions','cell_detection_runs'),
      'scientific_validation_classification_runs':('scientific_validation_sessions','cell_classification_runs'),
      'assessment_campaign_consumers':('experimental_campaigns','assessment_identities'),
    }
    for bridge,(left,right) in bridges.items():
        relationships.append(dict(relationship='N:M',name='via_'+bridge,parent_table=left,parent_columns='',child_table=right,child_columns='',cardinality='N:M',optional='',on_delete='ver FK',on_update='ver FK',deferrable='',initially_deferred='',via=bridge))
    write_or_compare(OUT/'dbv2_1_columns.csv',csv_text(['table','column','postgres_type','nullable','default','PK','FK','UNIQUE','CHECK','description'],columns),write)
    write_or_compare(OUT/'dbv2_1_relationships.csv',csv_text(['relationship','name','parent_table','parent_columns','child_table','child_columns','cardinality','optional','on_delete','on_update','deferrable','initially_deferred','via'],relationships),write)
    write_or_compare(OUT/'dbv2_1_table_details.md','# DBV2.1 — Fichas estructurales completas\n\nGeneradas del SQL propuesto. Complementan la definición estructural; no son una migración.\n\n'+'\n'.join(detail),write)
    write_or_compare(OUT/'dbv2_1_er_diagram.md','\n'.join(er+['```','','La FK describe cardinalidad máxima: 1:1 no impone por sí sola existencia de un hijo. Los triggers diferidos imponen completitud donde corresponde (E-04, evaluación, XAI).','N:M explícitas:']+[f'- `{a}` ↔ `{b}` por `{t}`.' for t,(a,b) in bridges.items()])+'\n',write)
    # SQL inventory and classifications, including removed objects.
    fnold={s.stmt.funcname[-1].sval:s.stmt for sql in oldstatements for s in parse_sql(sql) if isinstance(s.stmt,ast.CreateFunctionStmt)}
    fnnew={n.split('.')[-1]:s for n,s in c['functions'].items()}
    ft=['# DBV2.1 — Funciones y triggers','','Inventario exhaustivo de candidatas y objetivo; cuerpos completos en el SQL. No hay algoritmos científicos nuevos. REQUIRED_DB_INVARIANT protege identidad, completitud, atomicidad o inmutabilidad; TECHNICAL implementa canonización/hash o soporte. SOFTWARE_RESPONSIBILITY comprende selección de configuración, ejecución de procesos, cálculo de métricas y gestión física de archivos: ninguna función candidata de este inventario ejecuta esos algoritmos.','', 'E-04 conserva admisión SECURITY INVOKER, comparación NULL-safe, índices parciales y triggers diferidos. `v2_calibration_pair_guard` agrega concordancia con el objetivo de run_configurations. `v2_xai_comparison_guard` se reemplaza por completitud N:M. Las funciones de pgcrypto pertenecen a la extensión; no se copian como funciones propias.','', '| Función | Clasificación | Decisión | Garantía observable / motivo |','|---|---|---|---|']
    for name in sorted(fnold.keys()|fnnew.keys()):
        old=fnold.get(name); new=fnnew.get(name)
        action='REMOVE' if new is None else 'NEW' if old is None else 'KEEP' if norm(old)==norm(new) else 'MODIFY'
        codes=re.findall(r"RAISE EXCEPTION\s+'([^']+)'",render(new or old),re.I)
        reason='; '.join(codes) or 'Función auxiliar de identidad, consulta o transición atómica; definición completa en SQL.'
        if name=='prevent_model_governance_audit_mutation':reason='La tabla de backfill histórico queda fuera de una instalación vacía.'
        if name=='v2_xai_comparison_guard':reason='Sustituida por dbv21_xai_evaluation_complete para N:M; conserva compatibilidad entre explicaciones.'
        ft.append(f'| {name} | {classification(name)} | {action} | {reason.replace(chr(10)," ").replace("|","/")} |')
    ft+=['','| Trigger / tabla | Función | Clasificación | Decisión | Diferido |','|---|---|---|---|---|']
    trold={(s.stmt.relation.relname,s.stmt.trigname):s.stmt for sql in oldstatements for s in parse_sql(sql) if isinstance(s.stmt,ast.CreateTrigStmt)}
    for key in sorted(trold.keys()|c['triggers'].keys()):
        old=trold.get(key); new=c['triggers'].get(key); s=new or old; fn=s.funcname[-1].sval
        action='REMOVE' if new is None else 'NEW' if old is None else 'KEEP' if norm(old)==norm(new) else 'MODIFY'
        ft.append(f'| {key[1]} / {key[0]} | {fn} | {classification(fn)} | {action} | {s.deferrable}/{s.initdeferred} |')
    ft+=['','No se conservan funciones sólo por compatibilidad histórica: la tabla de auditoría backfill y su trigger desaparecen. Las guardas de campañas y TRAIN permanecen porque la exclusión entre sesiones concurrentes y la inmutabilidad de contratos requieren atomicidad en DB; planificar o ejecutar campañas pertenece a SW-v2.','']
    write_or_compare(OUT/'dbv2_1_functions_triggers.md','\n'.join(ft),write)
    oldviews={s.stmt.view.relname:s.stmt for sql in oldstatements for s in parse_sql(sql) if isinstance(s.stmt,ast.ViewStmt)}
    views=['# DBV2.1 — Views','','33 vistas normales; ninguna materializada. Las proyecciones no sustituyen la evidencia primaria. `classification_reports` y `confusion_matrices` ya eran vistas en la candidata y se registran como VIEW en la matriz por su origen como tablas legacy.','']
    for name,s in sorted(c['views'].items()):
        action='NEW' if name not in oldviews else 'KEEP' if norm(s)==norm(oldviews[name]) else 'MODIFY'
        deps=sorted({x['relname'] for x in walk(s.query) if x.get('@')=='RangeVar'})
        views += ['## '+name+' — '+action,'','Dependencias: '+', '.join(deps)+'. Lectura derivada; evita replicar estado.','```sql',render(s)+';','```','']
    write_or_compare(OUT/'dbv2_1_views.md','\n'.join(views),write)
    indexes=['# DBV2.1 — Índices','','PK y UNIQUE crean índices implícitos; se enumeran separadamente de CREATE INDEX. No duplicar índices exactos. Un prefijo más corto no se elimina sin evidencia de consultas; tampoco se añaden índices a todas las FK por defecto. Índices XAI nuevos cubren recorrido inverso de miembros, método, protocolo y anotación. E-04 conserva NULLS NOT DISTINCT y predicados de roles.','','## Implícitos por integridad','']
    for (t,n),co in c['constraints'].items():
        if co.contype in (CT.CONSTR_PRIMARY,CT.CONSTR_UNIQUE):indexes.append(f'- `{n}` en `{t}({", ".join(strings(co.keys))})`: '+('identidad primaria.' if co.contype==CT.CONSTR_PRIMARY else 'unicidad contractual / destino FK; '+render(co)+'.'))
    indexes+=['','## Explícitos','']
    for name,s in sorted(c['indexes'].items()):
        reason='Unicidad de identidad o exclusión condicionada; no es un índice de rendimiento prescindible.' if s.unique else 'Acceso por '+', '.join(x.name or render(x.expr) for x in s.indexParams)+' en '+s.relation.relname+'.'
        indexes+=['### '+name,'',reason,'```sql',render(s)+';','```','']
    indexes+=['## Cobertura de FK por prefijo','','Sin cobertura no significa FK inválida: su validación usa el índice UNIQUE del padre. Esta lista permite revisar coste de joins y borrados en DBV2.2; no presupone cargas medidas.','','| FK | Tabla hija | Prefijo cubierto |','|---|---|---|']
    for r in relationships:
        if r['relationship']!='FK':continue
        t=r['child_table']; cols=tuple(r['child_columns'].split(',')); covers=[]
        for n,co in table_constraints(c,t):
            if co.contype in (CT.CONSTR_PRIMARY,CT.CONSTR_UNIQUE) and strings(co.keys)[:len(cols)]==cols:covers.append(n)
        for n,s in c['indexes'].items():
            if s.relation.relname==t and s.whereClause is None and tuple(x.name for x in s.indexParams)[:len(cols)]==cols:covers.append(n)
        indexes.append('| '+r['name']+' | '+t+' | '+(', '.join(covers) or 'No; conservar sin índice adicional hasta justificar consulta/coste')+' |')
    write_or_compare(OUT/'dbv2_1_indexes.md','\n'.join(indexes)+'\n',write)
    # Static semantic checks, with no SQL evaluation/server.
    recall_checks=[render(co.raw_expr) for t,n in c['constraints'] for co in [c['constraints'][t,n]] if t=='run_configurations' and co.contype==CT.CONSTR_CHECK and 'clinical_target_recall' in colrefs(co.raw_expr)]
    assert any('clinical_target_recall > 0' in x and 'clinical_target_recall <= 1' in x for x in recall_checks)
    assert not re.search(r'(?:clinical_target_recall|target_recall)\s*=\s*0\.98',source)
    recall=next(r for r in columns if r['table']=='run_configurations' and r['column']=='clinical_target_recall')
    assert recall['nullable']=='NO' and not recall['default'] and recall['postgres_type']=='numeric'
    assert not {'xai_explanations','xai_error_analysis','schema_migrations','model_governance_backfill_audit'} & c['tables'].keys()
    assert c['primary']['xai_evaluation_members']==('evaluation_id','xai_evidence_id')
    assert not any(co.contype==CT.CONSTR_UNIQUE for _,co in table_constraints(c,'xai_evaluation_members'))
    assert next(r for r in columns if r['table']=='xai_artifacts' and r['column']=='sha256')['nullable']=='NO'
    assert next(r for r in columns if r['table']=='xai_quantitative_evaluations' and r['column']=='metric_value')['nullable']=='YES'
    assert 'XAI_MEMBERSHIP_HASH_MISMATCH' in source and 'XAI_AGREEMENT_INCOMPATIBLE' in source
    assert not any('xai_specialist_reviews' in render(co) for _,co in table_constraints(c,'xai_quantitative_evaluations'))
    assert not any(isinstance(parse_sql(s)[0].stmt,(ast.InsertStmt,ast.UpdateStmt,ast.DeleteStmt)) for s in statements)
    assert '\\i ' not in source and 'alembic/versions' not in source and 'adoption_v2' not in source
    # Namespace collision checks, including backing indexes; PostgreSQL constraint names are table-local.
    relations=set(c['tables'])|set(c['views']); backing=set()
    for (t,n),co in c['constraints'].items():
        assert len(n.encode())<=63, n
        if co.contype in (CT.CONSTR_PRIMARY,CT.CONSTR_UNIQUE): assert n not in backing; backing.add(n)
    assert not relations & backing and not relations & c['indexes'].keys() and not backing & c['indexes'].keys()
    assert all(len(n.encode())<=63 for n in relations|backing|c['indexes'].keys())
    idxsignatures=set()
    for s in c['indexes'].values():
        v=norm(s);v.pop('idxname',None); signature=json.dumps(v,sort_keys=True)
        assert signature not in idxsignatures, 'Duplicate index';idxsignatures.add(signature)
    # E-04 named constraints/indexes/functions/triggers must remain exactly intact.
    for sql in read_sql(ROOT/'alembic_v2/e04_contract.sql'):
        s=parse_sql(sql)[0].stmt
        if isinstance(s,ast.AlterTableStmt): assert all(norm(c['constraints'][s.relation.relname,cmd.def_.conname])==norm(cmd.def_) for cmd in s.cmds)
        elif isinstance(s,ast.IndexStmt): assert norm(c['indexes'][s.idxname])==norm(s)
        elif isinstance(s,ast.CreateFunctionStmt): assert norm(c['functions']['.'.join(strings(s.funcname))])==norm(s)
        elif isinstance(s,ast.CreateTrigStmt): assert norm(c['triggers'][s.relation.relname,s.trigname])==norm(s)
    for path,digest in json.loads((OUT/'dbv2_1_source_evidence.json').read_text()).items(): assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest, 'Source modified: '+path
    counts=collections.Counter(co.contype.name for co in c['constraints'].values()); actions=collections.Counter(r['action'] for r in matrix)
    report=dict(status='PASS_STATIC_ONLY',target_postgresql='17.9',parser_postgresql=get_postgresql_version(),sql_sha256=hashlib.sha256(SQL.read_bytes()).hexdigest(),tables=len(c['tables']),alembic_managed_tables=1,columns=len(columns),actions=dict(actions),foreign_keys=counts['CONSTR_FOREIGN'],checks=counts['CONSTR_CHECK'],unique_constraints=counts['CONSTR_UNIQUE'],unique_indexes=sum(s.unique for s in c['indexes'].values()),explicit_indexes=len(c['indexes']),implicit_indexes=len(backing),total_indexes=len(backing)+len(c['indexes']),functions=len(c['functions']),triggers=len(c['triggers']),views=len(c['views']),plpgsql_parsed=c['plpgsql'],e04_preserved=True,source_artifacts_unchanged=True,sql_executed=False,limitations=['Parser PostgreSQL 18.4; no certificación PostgreSQL 17.9.','PL/pgSQL parseado; semántica en servidor y concurrencia corresponden a DBV2.2.'])
    write_or_compare(OUT/'dbv2_1_static_validation.json',json.dumps(report,indent=2,ensure_ascii=False)+'\n',write)
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--write',action='store_true',help='Render derived documentation; never execute SQL'); args=ap.parse_args()
    print(json.dumps(build(args.write),indent=2,ensure_ascii=False))
