import type { ReactNode } from 'react';

interface ReportFiltersProps {
  children: ReactNode;
  hasActiveFilters: boolean;
  onClear: () => void;
}

export function ReportFilters({ children, hasActiveFilters, onClear }: ReportFiltersProps) {
  return (
    <section aria-label="Filtros del reporte" className="mb-4 grid grid-cols-[repeat(2,minmax(220px,1fr)) auto] items-end gap-3 rounded-card border border-[#dfe5f0] bg-surface p-3 max-[900px]:grid-cols-1">
      {children}
      <div className="flex items-center w-full">
        <button
          className="min-h-[38px] w-full rounded-lg border border-[#c7d2e6] bg-surface px-2.75 py-1.75 text-xs font-extrabold whitespace-nowrap text-accent-2 cursor-pointer hover:not-disabled:border-accent-2 hover:not-disabled:bg-[#eef3ff] disabled:text-muted-2 disabled:cursor-not-allowed focus-visible:outline-3 focus-visible:outline-[rgba(49,92,170,0.24)] focus-visible:outline-offset-2"
          disabled={!hasActiveFilters}
          onClick={onClear}
          type="button"
        >
          Limpiar filtros
        </button>
      </div>
    </section>
  );
}
