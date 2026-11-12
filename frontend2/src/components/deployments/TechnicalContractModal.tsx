import { useMemo,useState } from 'react';
import type { ModelContractCandidates } from '../../types/api';

export function TechnicalContractModal({contract,busy,onCancel,onSave}:{contract:ModelContractCandidates;busy:boolean;onCancel:()=>void;onSave:(selections:Record<string,string>)=>void}){
  const defaults=useMemo(()=>Object.fromEntries(contract.fields.map(field=>[field.key,field.proposed_source_id??''])),[contract]);
  const[selections,setSelections]=useState<Record<string,string>>(defaults);
  const ready=contract.fields.every(field=>field.status==='complete'||Boolean(selections[field.key]));
  return <div className="fixed inset-0 z-[1000] grid place-items-center bg-[rgba(16,24,43,0.58)] p-5"><div className="grid gap-3.5 w-[min(900px,calc(100vw-32px))] max-h-[calc(100vh-40px)] overflow-auto rounded-modal bg-surface p-6 shadow-modal" role="dialog" aria-modal="true" aria-labelledby="contract-title">
    <h2 className="m-0" id="contract-title">Generar versión productiva de {contract.model_name}</h2>
    <p className="m-0"><strong>{contract.model_name}{contract.version_number?` v${contract.version_number}`:''}</strong>. Los valores provienen de evidencia registrada; no se admiten rutas ni valores libres.</p>
    <div className="my-3.5 grid grid-cols-[repeat(auto-fit,minmax(190px,1fr))] gap-2.5">
      <span className="grid gap-1 rounded-lg border border-[#eef1f7] bg-subtle p-2.5 text-muted">Artifact<strong className="text-ink overflow-wrap-anywhere">{contract.production_package.artifact_id.slice(0,8)}…</strong></span>
      <span className="grid gap-1 rounded-lg border border-[#eef1f7] bg-subtle p-2.5 text-muted">SHA-256<strong className="text-ink overflow-wrap-anywhere">{contract.production_package.artifact_sha256.slice(0,12)}…</strong></span>
      <span className="grid gap-1 rounded-lg border border-[#eef1f7] bg-subtle p-2.5 text-muted">Training run<strong className="text-ink overflow-wrap-anywhere">{contract.training_run_id.slice(0,8)}…</strong></span>
      <span className="grid gap-1 rounded-lg border border-[#eef1f7] bg-subtle p-2.5 text-muted">Evaluación<strong className="text-ink overflow-wrap-anywhere">{contract.production_package.evaluation_run_ids[0]?.slice(0,8)??'No asociada'}…</strong></span>
      <span className="grid gap-1 rounded-lg border border-[#eef1f7] bg-subtle p-2.5 text-muted">Inmutable<strong className="text-ink overflow-wrap-anywhere">{contract.production_package.artifact_immutable?'Sí':'No'}</strong></span>
      <span className="grid gap-1 rounded-lg border border-[#eef1f7] bg-subtle p-2.5 text-muted">Framework<strong className="text-ink overflow-wrap-anywhere">{contract.production_package.framework??'No registrado'}</strong></span>
    </div>
    <div className="my-4 grid gap-2.5">{contract.fields.map(field=><section key={field.key} data-status={field.status} className="rounded-step border border-[#dbe2ef] p-3">
      <div className="flex justify-between gap-3"><strong>{field.label}</strong><span>{field.status==='complete'?'Registrado':field.status==='ready'?'Evidencia única':'Revisión requerida'}</span></div>
      {field.status==='complete'?<pre className="max-h-[130px] overflow-auto rounded-lg bg-[#f6f8fc] p-2 whitespace-pre-wrap overflow-wrap-anywhere">{JSON.stringify(field.current_value,null,2)}</pre>:field.candidates.length?
        <label className="grid gap-1.5 text-muted text-sm">Fuente<select className="w-full rounded-step border border-border-strong bg-surface p-2.25 text-ink-strong" value={selections[field.key]??''} onChange={event=>setSelections(value=>({...value,[field.key]:event.target.value}))}>
          <option value="">Seleccione evidencia</option>{field.candidates.map(candidate=><option key={candidate.source_id} value={candidate.source_id}>{candidate.source} · {candidate.source_id.slice(0,8)}</option>)}
        </select></label>:<p className="m-0">No existe evidencia inequívoca. Fuentes buscadas: {field.sources_searched.join(', ')}</p>}
      {selections[field.key]?<pre className="max-h-[130px] overflow-auto rounded-lg bg-[#f6f8fc] p-2 whitespace-pre-wrap overflow-wrap-anywhere">{JSON.stringify(field.candidates.find(item=>item.source_id===selections[field.key])?.value,null,2)}</pre>:null}
    </section>)}</div>
    <div className="flex justify-end gap-2.5"><button className="focus-visible:outline-3 focus-visible:outline-[#82a7ef] focus-visible:outline-offset-2" onClick={onCancel} disabled={busy}>Cancelar</button><button className="font-bold focus-visible:outline-3 focus-visible:outline-[#82a7ef] focus-visible:outline-offset-2" disabled={busy||!ready||!contract.production_package.artifact_immutable} onClick={()=>onSave(selections)}>{busy?'Creando…':'Crear versión inmutable'}</button></div>
  </div></div>;
}
