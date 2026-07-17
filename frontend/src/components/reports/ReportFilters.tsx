import type { ReactNode } from 'react';

interface ReportFiltersProps {
  children: ReactNode;
  hasActiveFilters: boolean;
  onClear: () => void;
}

export function ReportFilters({ children, hasActiveFilters, onClear }: ReportFiltersProps) {
  return (
    <section aria-label="Filtros del reporte" className="report-filters">
      {children}
      <div className="report-filter-actions">
        <button
          className="report-filter-clear"
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
