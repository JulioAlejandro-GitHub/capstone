"""Static source inventory. Does not import application modules or claim runtime coverage."""
from pathlib import Path
import ast,re,json,csv,hashlib,subprocess,collections
B=Path(__file__).resolve().parents[1];R=B.parents[2]
files=set();queue=[R/'frontend/src/pages/ModelComparison.tsx']
while queue:
 p=queue.pop()
 if p in files or not p.is_file():continue
 files.add(p);s=p.read_text()
 for rel in re.findall(r"(?:from\s+|import\s*)['\"]([^'\"]+)['\"]",s):
  if not rel.startswith('.'):continue
  target=p.parent/rel
  for suffix in ['', '.ts','.tsx','/index.ts','/index.tsx']:
   t=Path(str(target)+suffix).resolve()
   if t.is_file() and t.suffix in ['.ts','.tsx'] and t not in files:queue.append(t);break
for pattern in ['backend_api/app/services/scientific*.py','backend_api/app/repositories/scientific*.py','backend_api/app/schemas/scientific*.py','backend_api/app/*/*architecture*.py','backend_api/app/*/*assessment*.py','backend_api/app/*/*representation*.py','backend_api/app/*/*explain_generation*.py','backend_api/app/*/*activation_trace*.py','backend_api/app/*/*training_trajectories*.py','backend_api/app/*/*vit_structure*.py','backend_api/app/*/*dataset_samples*.py','backend_api/app/*/artifacts.py','backend_api/app/services/comparison_eligibility.py','backend_api/app/db.py','backend_api/app/routes/runs.py','backend_api/app/routes/catalog.py','backend_api/app/services/catalog.py','backend_api/app/services/training_summaries.py','backend_api/app/repositories/catalog.py','malaria_dl_local_project/src/malaria_dl/assessment/*.py','malaria_dl_local_project/src/malaria_dl/evaluation/*.py','malaria_dl_local_project/src/malaria_dl/training/*.py','malaria_dl_local_project/src/malaria_dl/models/*.py','malaria_dl_local_project/src/malaria_dl/explainability/*.py','malaria_dl_local_project/src/malaria_dl/science/*.py','malaria_dl_local_project/src/malaria_dl/data/{input_contract,preprocessing,sample_repository}.py']:
 files.update(R.glob(pattern))
files.update((R/'malaria_dl_local_project/src/malaria_dl/data').joinpath(n) for n in ['input_contract.py','preprocessing.py','sample_repository.py'])
tests=list((R/'backend_api/tests').glob('test_*.py'))+list((R/'malaria_dl_local_project/tests').glob('test_*.py'))+list((R/'frontend/tests').glob('*.mjs'));testtext={str(p.relative_to(R)):p.read_text(errors='replace') for p in tests};records=[];sources=[];endpoints=[]
for p in sorted(files):
 s=p.read_text();rel=str(p.relative_to(R));sources.append(dict(file=rel,lines=len(s.splitlines()),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 if p.suffix=='.py':
  tree=ast.parse(s)
  parent={child:node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
  for node in ast.walk(tree):
   if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
   owner=parent.get(node);name=(owner.name+'.' if isinstance(owner,ast.ClassDef) else '')+node.name
   snippet=ast.get_source_segment(s,node) or '';calls=sorted(set(ast.unparse(n.func) for n in ast.walk(node) if isinstance(n,ast.Call)));returns=[ast.unparse(n.value) for n in ast.walk(node) if isinstance(n,ast.Return) and n.value];tables=sorted(set(re.findall(r'\b(?:FROM|JOIN|INTO|UPDATE)\s+([a-z_][a-z_0-9]*)',snippet,re.I)));guard=[line.strip() for line in snippet.splitlines() if any(t in line for t in ['require(','raise ','assert ','HTTPException','isfinite'])]
   refs=[f for f,t in testtext.items() if re.search(r'\b'+re.escape(node.name)+r'\b',t)];category='Representaciones' if any(t in rel for t in ['represent','activation_trace']) else 'Explicabilidad' if any(t in rel for t in ['explain','xai']) else 'Arquitectura' if any(t in rel for t in ['architecture','vit_structure','models/']) else 'Aprendizaje / Clínico / Errores / Trazabilidad'
   record=dict(function=name,file=rel,line=node.lineno,end_line=node.end_lineno,category=category,purpose=(ast.get_docstring(node) or 'Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución.')[:650],inputs=ast.unparse(node.args),origin='; '.join(tables) or 'Argumentos / memoria / archivo según llamadas',algorithm='; '.join(calls),formula='Ver fichas matemáticas del informe 05; cuerpo enlazado para helpers',outputs='; '.join(returns)[:1400],persistence='; '.join(tables) if re.search(r'\b(INSERT|UPDATE|DELETE)\b',snippet) else ('Archivo' if any(v in snippet for v in ['.write','save_artifacts','save_arrays','os.link']) else 'Sin escritura SQL identificada'),consumer='; '.join(str(q.relative_to(R)) for q in files if q!=p and re.search(r'\b'+re.escape(node.name)+r'\b',q.read_text(errors='replace')))[:1000],visualization=category,validations='; '.join(guard)[:1000],limitations='Inventario estático; llamadas no equivalen a ejecución; consumidor por referencia textual',tests='; '.join(refs) or 'Sin referencia nominal localizada')
   records.append(record)
   for d in node.decorator_list:
    if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and isinstance(d.func.value,ast.Name) and d.func.value.id=='router':endpoints.append(dict(method=d.func.attr.upper(),path=ast.unparse(d.args[0]) if d.args else '',file=rel,line=node.lineno,function=name,parameters=record['inputs'],decorator=ast.unparse(d)))
 else:
  ast_path=B/'evidence/typescript_functions.json'
  for item in json.loads(ast_path.read_text()) if ast_path.exists() else []:
   if item['file']!=rel:continue
   name=item['function']
   records.append(dict(function=name,file=rel,line=item['line'],end_line=item['end_line'],category='Frontend: cierre transitivo de imports del módulo',purpose=item['jsdoc'] or item['kind']+'; operación exacta en llamadas y cuerpo',inputs=item['inputs'],origin='Props / estado / API según llamadas; no ejecución acreditada',algorithm='; '.join(item['calls']),formula='Ver fichas matemáticas del informe 05',outputs=item['returns'],persistence='Consultar llamadas: no atribuir escritura a todos los callbacks',consumer='Cierre estático de imports; no todos los helpers del archivo son invocados por esta ruta',visualization='Componente y ficha del informe 05',validations='; '.join(item['guards'])[:1500],limitations='AST TypeScript; callbacks identificados por línea. Inventario de fuentes es superconjunto de funciones utilizadas, no perfil de ejecución.',tests='; '.join(f for f,t in testtext.items() if name.split('.')[0] in t) or 'Sin referencia nominal localizada'))

def csvwrite(name,rows):
 with (B/'csv'/f'{name}.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
csvwrite('functions',records);csvwrite('sources',sources);csvwrite('endpoints_static',endpoints)
(B/'evidence/source_files.json').write_text(json.dumps(sources,indent=2))
md=['# CAPSTONE-P3-04 — Catálogo de funciones','\nInventario estático reproducible. Las fichas matemáticas y contratos ejecutados están en el documento 05; este catálogo conserva entradas, llamadas, retornos, controles, consumidores textuales y tests encontrados. Las coincidencias textuales no acreditan cobertura dinámica ni que una función haya sido invocada.\n','Todos los campos solicitados se entregan por fila en [functions.csv](csv/functions.csv). Índice de fuentes con SHA-256: [sources.csv](csv/sources.csv). Las líneas corresponden al workspace auditado, incluidas modificaciones previas.\n']
for file,items in __import__('itertools').groupby(records,key=lambda r:r['file']):
 md+=['\n## '+file+'\n','| Función | Línea | Propósito / operación | Pruebas nominales |','|---|---:|---|---|']
 for r in items:md.append('| '+r['function']+' | ['+str(r['line'])+'](../../../'+file+'#L'+str(r['line'])+') | '+r['purpose'].replace('\n',' ').replace('|','/')[:220]+' | '+r['tests'].replace('|','/')+' |')
(B/'CAPSTONE_P3_04_CATALOGO_FUNCIONES.md').write_text('\n'.join(md)+'\n')
# Runtime/local source identity only, without importing application modules.
core=[x for x in sources if x['file'].startswith('backend_api/app/') or x['file'].startswith('malaria_dl_local_project/src/malaria_dl/assessment/')]
paths=['/app/'+x['file'].removeprefix('backend_api/') if x['file'].startswith('backend_api/') else '/app/'+x['file'] for x in core]
code='import hashlib,json,pathlib;paths='+repr(paths)+';print(json.dumps({p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() if pathlib.Path(p).is_file() else None for p in paths}))'
p=subprocess.run(['docker','exec','capstone_backend','python','-B','-c',code],text=True,capture_output=True,check=True);remote=json.loads(p.stdout)
csvwrite('runtime_source_identity',[dict(file=s['file'],workspace_sha256=s['sha256'],container_sha256=remote[p],equal=s['sha256']==remote[p]) for s,p in zip(core,paths)])
print('Catalog:',len(sources),'files,',len(records),'named functions,',len(endpoints),'route declarations')
