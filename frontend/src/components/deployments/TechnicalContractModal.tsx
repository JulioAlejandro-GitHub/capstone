import { useMemo,useState } from 'react';
import type { ModelContractCandidates } from '../../types/api';

export function TechnicalContractModal({contract,busy,onCancel,onSave}:{contract:ModelContractCandidates;busy:boolean;onCancel:()=>void;onSave:(selections:Record<string,string>)=>void}){
  const defaults=useMemo(()=>Object.fromEntries(contract.fields.map(field=>[field.key,field.proposed_source_id??''])),[contract]);
  const[selections,setSelections]=useState<Record<string,string>>(defaults);
  const ready=contract.fields.every(field=>field.status==='complete'||Boolean(selections[field.key]));
  return <div className="modal-backdrop"><div className="production-modal contract-modal" role="dialog" aria-modal="true" aria-labelledby="contract-title">
    <h2 id="contract-title">Generar versión productiva de {contract.model_name}</h2>
    <p><strong>{contract.model_name}{contract.version_number?` v${contract.version_number}`:''}</strong>. Los valores provienen de evidencia registrada; no se admiten rutas ni valores libres.</p>
    <div className="facts-grid package-preview">
      <span>Artifact<strong>{contract.production_package.artifact_id.slice(0,8)}…</strong></span>
      <span>SHA-256<strong>{contract.production_package.artifact_sha256.slice(0,12)}…</strong></span>
      <span>Training run<strong>{contract.training_run_id.slice(0,8)}…</strong></span>
      <span>Evaluación<strong>{contract.production_package.evaluation_run_ids[0]?.slice(0,8)??'No asociada'}…</strong></span>
      <span>Inmutable<strong>{contract.production_package.artifact_immutable?'Sí':'No'}</strong></span>
      <span>Framework<strong>{contract.production_package.framework??'No registrado'}</strong></span>
    </div>
    <div className="contract-preview">{contract.fields.map(field=><section key={field.key} data-status={field.status}>
      <div><strong>{field.label}</strong><span>{field.status==='complete'?'Registrado':field.status==='ready'?'Evidencia única':'Revisión requerida'}</span></div>
      {field.status==='complete'?<pre>{JSON.stringify(field.current_value,null,2)}</pre>:field.candidates.length?
        <label>Fuente<select value={selections[field.key]??''} onChange={event=>setSelections(value=>({...value,[field.key]:event.target.value}))}>
          <option value="">Seleccione evidencia</option>{field.candidates.map(candidate=><option key={candidate.source_id} value={candidate.source_id}>{candidate.source} · {candidate.source_id.slice(0,8)}</option>)}
        </select></label>:<p>No existe evidencia inequívoca. Fuentes buscadas: {field.sources_searched.join(', ')}.</p>}
      {selections[field.key]?<pre>{JSON.stringify(field.candidates.find(item=>item.source_id===selections[field.key])?.value,null,2)}</pre>:null}
    </section>)}</div>
    <div className="modal-actions"><button onClick={onCancel} disabled={busy}>Cancelar</button><button className="primary-action" disabled={busy||!ready||!contract.production_package.artifact_immutable} onClick={()=>onSave(selections)}>{busy?'Creando…':'Crear versión inmutable'}</button></div>
  </div></div>;
}
