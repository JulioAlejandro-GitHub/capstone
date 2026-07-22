import { useEffect,useState } from 'react';
import { DataTable } from '../components/DataTable';import { Loading } from '../components/Loading';import { StatusBadge } from '../components/StatusBadge';
import { api } from '../services/api';import type { DeploymentRow } from '../types/api';import { formatDate,formatMetric } from '../utils/format';
const short=(value:string)=>`${value.slice(0,8)}…`;
export function Deployments({datasource}:{datasource:string}){const[rows,setRows]=useState<DeploymentRow[]>([]);const[loading,setLoading]=useState(true);const[error,setError]=useState<string|null>(null);
  useEffect(()=>{setLoading(true);api.getDeployments(datasource).then((r)=>setRows(r.items)).catch((e)=>setError(String(e))).finally(()=>setLoading(false));},[datasource]);
  if(loading)return <div className="page"><Loading/></div>;if(error)return <div className="page"><div className="panel warning-panel"><h1>Error al cargar deployments</h1><p>{error}</p></div></div>;
  return <section className="page"><div className="page-title"><div><h1>Despliegues</h1><p>Revisiones operativas y aliases controlados. Las acciones requieren permisos administrativos no disponibles en esta interfaz.</p></div></div>
    <div className="panel"><DataTable rows={rows} emptyText="No existen deployments registrados." getRowKey={(r)=>r.id} columns={[
      {header:'Deployment',render:(r)=><><strong>{r.deployment_name}</strong><br/><code>{short(r.id)}</code></>},{header:'Environment',render:(r)=>r.environment},
      {header:'Alias',render:(r)=><strong>{r.alias}</strong>},{header:'Model version',render:(r)=><code>{short(r.model_version_id)}</code>},
      {header:'Estado',render:(r)=><StatusBadge status={r.status}/>},{header:'Threshold',render:(r)=>formatMetric(r.threshold_value)},
      {header:'Activación',render:(r)=>formatDate(r.deployed_at)},{header:'Retiro',render:(r)=>formatDate(r.retired_at)},{header:'Responsable',render:(r)=>r.deployed_by??'—'},]}/></div></section>}
