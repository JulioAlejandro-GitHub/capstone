import { useEffect, useState } from 'react';

import { useAuth } from '../auth';
import { ApiError, api, type AnalysisRun, type EligibleBatch, type QualityQueueItem, type QueuePriority } from '../services/api';

const pct = (value:number|null) => value == null ? '—' : `${(value*100).toFixed(1)} %`;
const metric = (value:number|null,digits=4) => value == null ? '—' : value.toFixed(digits);

function AuthenticatedPreview({imageId,name}:{imageId:string;name:string}) {
  const [url,setUrl]=useState<string|null>(null);
  useEffect(()=>{
    let active=true;let objectUrl:string|null=null;
    api.getMicroscopyImageBlob(imageId).then(value=>{objectUrl=value;if(active)setUrl(value);}).catch(()=>undefined);
    return ()=>{active=false;if(objectUrl)URL.revokeObjectURL(objectUrl);};
  },[imageId]);
  return url?<img src={url} alt={`Preview técnico de ${name}`} loading="lazy" />:<span>Preview no disponible</span>;
}

export function SmearAnalysis() {
  const { user } = useAuth();
  const [subject,setSubject]=useState('');
  const [sample,setSample]=useState('');
  const [batches,setBatches]=useState<EligibleBatch[]>([]);
  const [run,setRun]=useState<AnalysisRun|null>(null);
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState('');
  const [comment,setComment]=useState('');
  const [priority,setPriority]=useState<QueuePriority>(50);
  const [queue,setQueue]=useState<QualityQueueItem[]>([]);
  const [retryPriorities,setRetryPriorities]=useState<Record<string,QueuePriority>>({});
  const canCreate=Boolean(user?.permissions.includes('scientific.analysis.create'));
  const canExecute=Boolean(user?.permissions.includes('scientific.analysis.quality.execute'));
  const canReview=Boolean(user?.permissions.includes('scientific.analysis.quality.review'));
  const canQueueCreate=Boolean(user?.permissions.includes('scientific.analysis.queue.create'));
  const canQueueExecute=Boolean(user?.permissions.includes('scientific.analysis.queue.execute'));
  const canQueueRetry=Boolean(user?.permissions.includes('scientific.analysis.queue.retry'));

  async function load() {
    try { setBatches((await api.getEligibleBatches({subject_code:subject||undefined,sample_code:sample||undefined})).items); }
    catch { setMessage('No fue posible cargar los lotes elegibles.'); }
  }
  useEffect(()=>{ void load(); },[]);
  async function loadQueue() {
    try { setQueue((await api.getQualityQueue()).items); }
    catch { setMessage('No fue posible actualizar la cola.'); }
  }
  useEffect(()=>{ void loadQueue(); },[]);
  async function action(task:()=>Promise<AnalysisRun>) {
    setBusy(true);setMessage('');
    try { setRun(await task()); }
    catch(error) { setMessage(error instanceof ApiError ? 'La operación fue rechazada por el backend.' : 'No fue posible completar la operación.'); }
    finally { setBusy(false); }
  }
  async function create(batchId:string) { await action(()=>api.createAnalysisRun(batchId)); }
  async function assess() { if(run) await action(()=>api.executeQuality(run.id)); }
  async function review(decision:'approve_with_warnings'|'reject') {
    if(!run||!comment.trim()) return;
    if(decision==='reject'&&!window.confirm('¿Confirmas el bloqueo técnico de esta ejecución?')) return;
    await action(()=>api.reviewQuality(run.id,decision,comment.trim()));setComment('');
  }
  async function enqueue() {
    if(!run)return;setBusy(true);setMessage('');
    try { await api.enqueueQuality(run.id,priority);await loadQueue();setMessage('Solicitud agregada a la cola.'); }
    catch { setMessage('No fue posible agregar la solicitud a la cola.'); }
    finally { setBusy(false); }
  }
  async function executeQueued(item:QualityQueueItem) {
    setBusy(true);setMessage('');
    try { await api.executeQueueItem(item.queue_item_id);await loadQueue();setRun(await api.getAnalysisRun(item.analysis_run_id)); }
    catch { setMessage('La ejecución manual falló. Revisa el estado y el error seguro en la cola.');await loadQueue(); }
    finally { setBusy(false); }
  }
  async function retry(item:QualityQueueItem) {
    setBusy(true);setMessage('');
    try { await api.retryQueueItem(item.queue_item_id,retryPriorities[item.queue_item_id]??item.priority);await loadQueue();setMessage('Solicitud devuelta a la cola; aún requiere “Ejecutar ahora”.'); }
    catch { setMessage('No fue posible reintentar la solicitud.'); }
    finally { setBusy(false); }
  }
  const priorityLabel=(value:number)=>value===100?'Máxima':value===1?'Mínima':'Normal';
  const statusLabel:Record<QualityQueueItem['status'],string>={queued:'En cola',running:'En ejecución',completed:'Completada',failed:'Fallida'};
  const counts=run?.images.reduce((acc,item)=>({...acc,[item.quality_verdict??'pending']:(acc[item.quality_verdict??'pending']??0)+1}),{} as Record<string,number>)??{};
  return <section className="page smear-analysis">
    <header className="page-title"><div><h1>Control técnico de calidad</h1>
      <p>Evalúa preparación técnica reproducible. No diagnostica malaria ni valida calidad clínica.</p></div></header>
    <div className="quality-filters">
      <label>Paciente<input value={subject} onChange={e=>setSubject(e.target.value)} /></label>
      <label>Muestra<input value={sample} onChange={e=>setSample(e.target.value)} /></label>
      <button type="button" onClick={load}>Buscar</button>
    </div>
    <div className="table-wrap"><table><thead><tr><th>Paciente</th><th>Muestra</th><th>Frotis</th><th>Origen</th><th>Imágenes</th><th>Ingesta</th><th>Acción</th></tr></thead>
      <tbody>{batches.map(batch=><tr key={batch.id}><td>{batch.subject_code}</td><td>{batch.sample_code}</td><td>{batch.slide_code}</td>
        <td>{batch.source_system??batch.acquisition_origin}</td><td>{batch.received_image_count}</td><td>{batch.status}</td>
        <td><button disabled={busy||!canCreate} onClick={()=>create(batch.id)}>{batch.previous_run_code?'Abrir o crear':'Crear ejecución'}</button></td></tr>)}</tbody></table></div>
    {run?<section className="quality-run" aria-live="polite">
      <header><div><h2>{run.run_code}</h2><p>{run.subject_code} · {run.sample_code} · {run.slide_code}</p></div>
        <span className={`quality-verdict ${run.quality_gate_status}`}>{run.quality_gate_status}</span></header>
      <dl className="quality-summary"><div><dt>Perfil</dt><dd>{run.quality_profile_key} v{run.quality_profile_version}</dd></div>
        <div><dt>Estado</dt><dd>{busy?'Procesando…':run.run_status} · {run.active_stage}</dd></div>
        <div><dt>Solicitante</dt><dd>{run.requested_by_username}</dd></div>
        <div><dt>Resultado</dt><dd>{counts.pass??0} aprobadas · {counts.warning??0} advertencias · {(counts.fail??0)+(counts.error??0)} bloqueadas</dd></div>
        <div><dt>Lista para análisis</dt><dd>{run.ready_for_analysis?'Sí':'No'}</dd></div></dl>
      {['quality_pending','created'].includes(run.run_status)?<button disabled={busy||!canExecute} onClick={assess}>{busy?`Evaluando ${run.input_image_count} imágenes…`:'Ejecutar control técnico'}</button>:null}
      {['quality_pending','created'].includes(run.run_status)?<div className="queue-enqueue">
        <label>Prioridad<select aria-label="Prioridad de la solicitud" value={priority} onChange={e=>setPriority(Number(e.target.value) as QueuePriority)}>
          <option value={1}>Mínima — 1</option><option value={50}>Normal — 50</option><option value={100}>Máxima — 100</option>
        </select></label>
        <button disabled={busy||!canQueueCreate} onClick={enqueue}>Agregar a la cola</button>
      </div>:null}
      {run.quality_gate_status==='warning'&&canReview?<div className="quality-review"><label>Comentario técnico obligatorio
        <textarea value={comment} onChange={e=>setComment(e.target.value)} /></label>
        <button disabled={busy||!comment.trim()} onClick={()=>review('approve_with_warnings')}>Aprobar con advertencias</button>
        <button className="danger" disabled={busy||!comment.trim()} onClick={()=>review('reject')}>Rechazar</button></div>:null}
      <div className="quality-images">{run.images.map(image=><article key={image.id} className="quality-image">
        <div className="quality-preview"><AuthenticatedPreview imageId={image.microscopy_image_id} name={image.original_filename} /></div>
        <h3>{image.sequence_number}. {image.original_filename}</h3>
        <p><span className={`quality-verdict ${image.quality_verdict??'pending'}`}>{image.quality_verdict??'pending'}</span> · {image.input_width_px}×{image.input_height_px} · SHA {image.input_sha256.slice(0,12)}…</p>
        <dl><div><dt>Integridad</dt><dd>{image.integrity_verified?'Verificada':'Pendiente/no verificada'}</dd></div>
          <div><dt>Nitidez (Laplaciano)</dt><dd>{metric(image.laplacian_variance)}</dd></div><div><dt>Brillo</dt><dd>{metric(image.brightness_mean)}</dd></div>
          <div><dt>Contraste</dt><dd>{metric(image.contrast_p95_p05)}</dd></div><div><dt>Entropía</dt><dd>{metric(image.entropy_bits,2)} bits</dd></div>
          <div><dt>Píxeles oscuros</dt><dd>{pct(image.dark_pixel_ratio)}</dd></div><div><dt>Píxeles saturados</dt><dd>{pct(image.bright_pixel_ratio)}</dd></div>
          <div><dt>Área útil</dt><dd>{pct(image.usable_field_ratio)}</dd></div></dl>
        {image.warning_codes?.length?<p>Advertencias: {image.warning_codes.join(', ')}</p>:null}
        {image.failure_codes?.length?<p>Fallos: {image.failure_codes.join(', ')}</p>:null}
      </article>)}</div>
    </section>:null}
    <section className="quality-queue">
      <header><div><h2>Cola de solicitudes</h2><p>Procesamiento y reintentos exclusivamente manuales.</p></div>
        <button type="button" disabled={busy} onClick={loadQueue}>Actualizar cola</button></header>
      <div className="table-wrap"><table><thead><tr><th>Prioridad</th><th>Run</th><th>Paciente</th><th>Muestra</th>
        <th>Estado</th><th>Intentos</th><th>Solicitado por</th><th>Fecha de solicitud</th><th>Último error</th><th>Acciones</th></tr></thead>
        <tbody>{queue.map(item=><tr key={item.queue_item_id}>
          <td>{priorityLabel(item.priority)} — {item.priority}</td><td>{item.run_code}</td><td>{item.subject_code}</td><td>{item.sample_code}</td>
          <td>{statusLabel[item.status]}</td><td>{item.attempt_count}</td><td>{item.requested_by_username}</td>
          <td>{new Date(item.requested_at).toLocaleString()}</td><td>{item.last_error_message??'—'}</td><td>
            {item.status==='queued'?<button disabled={busy||!canQueueExecute} onClick={()=>executeQueued(item)}>Ejecutar ahora</button>:null}
            {item.status==='running'?<button disabled>En ejecución</button>:null}
            {item.status==='completed'?<button onClick={()=>api.getAnalysisRun(item.analysis_run_id).then(setRun)}>Abrir detalle</button>:null}
            {item.status==='failed'?<div className="queue-retry"><select aria-label={`Nueva prioridad para ${item.run_code}`}
              value={retryPriorities[item.queue_item_id]??item.priority}
              onChange={e=>setRetryPriorities(values=>({...values,[item.queue_item_id]:Number(e.target.value) as QueuePriority}))}>
              <option value={1}>Mínima — 1</option><option value={50}>Normal — 50</option><option value={100}>Máxima — 100</option>
            </select><button disabled={busy||!canQueueRetry} onClick={()=>retry(item)}>Reintentar</button></div>:null}
          </td></tr>)}
          {!queue.length?<tr><td colSpan={10}>No hay solicitudes en la cola.</td></tr>:null}</tbody></table></div>
    </section>
    {message?<p role="alert">{message}</p>:null}
  </section>;
}
