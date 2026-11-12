import type { ModelProductionReadiness } from '../../types/api';

const labels = ['Versión inmutable y contrato técnico', 'Validación', 'Aprobación', 'Publicación en producción'];

export function ProductionStepIndicator({ readiness }: { readiness: ModelProductionReadiness }) {
  return (
    <ol className="mt-1 mb-5 grid grid-cols-4 gap-2 list-none p-0 max-[700px]:grid-cols-1" aria-label="Progreso de promoción a producción">
      {labels.map((label, index) => {
        const step = index + 1;
        const completed = step < readiness.current_step || (step === 4 && readiness.production_status.available_for_inference);
        const current = step === readiness.current_step && !completed;
        return (
          <li
            key={label}
            data-state={completed ? 'complete' : current ? 'current' : 'pending'}
            className="flex items-center gap-2 rounded-step border border-[#dbe2ef] bg-surface p-2.75 text-fg data-[state=complete]:border-[#8bc9a2] data-[state=complete]:bg-[#effaf3] data-[state=complete]:text-step-complete data-[state=current]:border-[#758bc7] data-[state=current]:ring-2 data-[state=current]:ring-[#e8edff] data-[state=current]:text-step-current data-[state=pending]:text-step-pending"
          >
            <span
              aria-hidden="true"
              className={`grid h-6.5 w-6.5 place-items-center rounded-full ${completed ? 'bg-[#23864a] text-white' : 'bg-[#e9edf5] text-[#172033]'}`}
            >
              {completed ? '✓' : step}
            </span>
            <strong>{label}{step === 4 && completed ? ' activa' : ''}</strong>
          </li>
        );
      })}
    </ol>
  );
}
