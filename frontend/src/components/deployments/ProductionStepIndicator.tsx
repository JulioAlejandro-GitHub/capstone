import type { ModelProductionReadiness } from '../../types/api';

const labels=['Versión inmutable y contrato técnico','Validación','Aprobación','Publicación en producción'];

export function ProductionStepIndicator({readiness}:{readiness:ModelProductionReadiness}){
  return <ol className="production-steps" aria-label="Progreso de promoción a producción">
    {labels.map((label,index)=>{
      const step=index+1;const completed=step<readiness.current_step||(step===4&&readiness.production_status.available_for_inference);
      const current=step===readiness.current_step&&!completed;
      return <li key={label} data-state={completed?'complete':current?'current':'pending'}>
        <span aria-hidden="true">{completed?'✓':step}</span><strong>{label}{step===4&&completed?' activa':''}</strong>
      </li>;
    })}
  </ol>;
}
