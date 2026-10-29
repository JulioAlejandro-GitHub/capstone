import { useMemo, useState, type ReactNode } from 'react';
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_ColumnFiltersState,
  type MRT_PaginationState,
  type MRT_RowSelectionState,
  type MRT_Updater,
} from 'material-react-table';
import { MRT_Localization_ES } from 'material-react-table/locales/es';
import { ThemeProvider, createTheme } from '@mui/material/styles';

import type { TrainingSummary } from '../../types/api';
import { generateRunAutoAnalysis, resolveRunConfusion, resolveRunReportMetrics } from '../../utils/runReport';
import { RunAnalysisCell, RunIdentityCell, RunModelCell, RunResultsCell } from './RunSummaryRow';

export const TRAINING_RUNS_PAGE_SIZE = 7;
export const ACTIVE_MODEL_FILTER = 'active:';
export const MISSING_MODEL_FILTER = 'missing:';
export const MODEL_FILTER_PREFIX = 'model:';
const OPTIMIZER_FILTER_PREFIX = 'optimizer:';
const STATUS_FILTER_PREFIX = 'status:';

const label = (value: string | null | undefined) => value?.trim() || null;

export function modelFilterValue(modelName: string | null | undefined): string {
  const model = label(modelName);
  return model ? `${MODEL_FILTER_PREFIX}${model}` : MISSING_MODEL_FILTER;
}

const sortedOptions = (options: Map<string, string>) => Array.from(options, ([value, text]) => ({ value, text }))
  .sort((left, right) => left.text.localeCompare(right.text, 'es', { sensitivity: 'base' }));

const metricColumns = [
  { id: 'recall', header: 'Recall' },
  { id: 'specificity', header: 'Specificity' },
  { id: 'f2', header: 'F2' },
  { id: 'auc', header: 'AUC' },
] as const;

// MUI overlays (filter menus, pagination) must render inside a modal <dialog>: a body portal sits below its top layer.
const pageTheme = createTheme({ typography: { fontFamily: 'inherit' } });
const dialogTheme = createTheme({
  typography: { fontFamily: 'inherit' },
  components: {
    MuiPopover: { defaultProps: { disablePortal: true } },
    MuiPopper: { defaultProps: { disablePortal: true } },
  },
});

export interface TrainingRunsSelection {
  ids: string[];
  maximum?: number;
  /** Whether a not-yet-selected TRAIN may be added; selected rows can always be removed. */
  canSelect: (training: TrainingSummary) => boolean;
  onChange: (id: string, selected: boolean) => void;
}

interface TrainingRunsTableProps {
  trainings: TrainingSummary[];
  variant?: 'full' | 'compact';
  inDialog?: boolean;
  onRunSelect: (runId: string) => void;
  isActive: (training: TrainingSummary) => boolean;
  /** Replaces the automatic analysis column body (e.g. to wire the release panel toggle). */
  renderAnalysis?: (training: TrainingSummary) => ReactNode;
  renderDetailPanel?: (training: TrainingSummary) => ReactNode;
  selection?: TrainingRunsSelection;
  extraColumns?: MRT_ColumnDef<TrainingSummary>[];
  modelFilter?: string;
  onModelFilterChange?: (value: string) => void;
  title?: ReactNode;
}

/**
 * Client-side TRAIN report (the summaries endpoint returns the whole bounded collection): global search, faceted
 * filters per column, sorting and 7-row pages. Selection is keyed by run_id, so it survives paging and filtering.
 */
export function TrainingRunsTable({
  trainings, variant = 'full', inDialog = false, onRunSelect, isActive, renderAnalysis, renderDetailPanel,
  selection, extraColumns = [], modelFilter = '', onModelFilterChange, title,
}: TrainingRunsTableProps) {
  const [columnFilters, setColumnFilters] = useState<MRT_ColumnFiltersState>(
    () => modelFilter ? [{ id: 'model', value: modelFilter }] : [],
  );
  const [globalFilter, setGlobalFilter] = useState('');
  const [pagination, setPagination] = useState<MRT_PaginationState>({ pageIndex: 0, pageSize: TRAINING_RUNS_PAGE_SIZE });
  const [onlySelected, setOnlySelected] = useState(false);
  const activeTraining = trainings.find(isActive) ?? null;
  const runFilter = columnFilters.find(filter => filter.id === 'run')?.value;

  const updateFilters = (updater: MRT_Updater<MRT_ColumnFiltersState>) => {
    const next = typeof updater === 'function' ? updater(columnFilters) : updater;
    setColumnFilters(next);
    setPagination(current => ({ ...current, pageIndex: 0 }));
    const model = String(next.find(filter => filter.id === 'model')?.value ?? '');
    if (model !== modelFilter) onModelFilterChange?.(model);
  };

  const toggleActiveModel = () => updateFilters(current => runFilter === ACTIVE_MODEL_FILTER
    ? current.filter(filter => filter.id !== 'run')
    : [...current.filter(filter => filter.id !== 'run'), { id: 'run', value: ACTIVE_MODEL_FILTER }]);

  const { runOptions, modelOptions, analysisOptions } = useMemo(() => {
    const statuses = new Map<string, string>();
    const models = new Map<string, string>();
    const optimizers = new Map<string, string>();
    const analyses = new Set<string>();
    trainings.forEach(training => {
      statuses.set(`${STATUS_FILTER_PREFIX}${training.status}`, `Estado: ${training.status}`);
      models.set(modelFilterValue(training.model_name), `Modelo: ${label(training.model_name) ?? 'No registrado'}`);
      const optimizer = label(training.optimizer);
      if (optimizer) optimizers.set(`${OPTIMIZER_FILTER_PREFIX}${optimizer}`, `Optimizer: ${optimizer}`);
      analyses.add(generateRunAutoAnalysis(training).title);
    });
    return {
      runOptions: [{ value: ACTIVE_MODEL_FILTER, text: 'Modelo en Estado Activo' }, ...sortedOptions(statuses)],
      modelOptions: [...sortedOptions(models), ...sortedOptions(optimizers)],
      analysisOptions: Array.from(analyses).sort((left, right) => left.localeCompare(right, 'es')),
    };
  }, [trainings]);

  const columns = useMemo<MRT_ColumnDef<TrainingSummary>[]>(() => [
    {
      id: 'run', header: 'RUN', size: 250,
      // Searchable text; ordering is by start date.
      accessorFn: row => [row.run_name, row.run_id, row.dataset_name, row.dataset_version_id, row.status].filter(Boolean).join(' '),
      sortingFn: (left, right) => (left.original.started_at ?? '').localeCompare(right.original.started_at ?? ''),
      filterVariant: 'select', filterSelectOptions: runOptions,
      filterFn: (row, _id, value: string) => !value
        || (value === ACTIVE_MODEL_FILTER ? isActive(row.original) : `${STATUS_FILTER_PREFIX}${row.original.status}` === value),
      Cell: ({ row }) => <div className="report-cell report-run-cell">
        <RunIdentityCell run={row.original} variant={variant} processKind="training" />
      </div>,
    },
    {
      id: 'model', header: 'Modelo', size: 270,
      accessorFn: row => [row.model_name, row.optimizer].filter(Boolean).join(' '),
      filterVariant: 'select', filterSelectOptions: modelOptions,
      filterFn: (row, _id, value: string) => !value || (value.startsWith(OPTIMIZER_FILTER_PREFIX)
        ? `${OPTIMIZER_FILTER_PREFIX}${label(row.original.optimizer)}` === value
        : modelFilterValue(row.original.model_name) === value),
      Cell: ({ row }) => <div className="report-cell report-model-cell">
        <RunModelCell run={row.original} variant={variant} processKind="training" />
      </div>,
    },
    {
      id: 'results', header: 'Resultados (orden por FN)', size: 340,
      accessorFn: row => resolveRunConfusion(row).fn ?? undefined, sortUndefined: 'last',
      filterVariant: 'range', enableGlobalFilter: false,
      Cell: ({ row }) => <div className="report-cell report-results-cell">
        <RunResultsCell run={row.original} variant={variant} />
      </div>,
    },
    ...metricColumns.map(({ id, header }): MRT_ColumnDef<TrainingSummary> => ({
      id, header, size: 120, accessorFn: row => resolveRunReportMetrics(row)[id] ?? undefined, sortUndefined: 'last',
      filterVariant: 'range', enableGlobalFilter: false,
      Cell: ({ cell }) => cell.getValue<number | undefined>()?.toFixed(4) ?? '—',
    })),
    {
      id: 'analysis', header: 'Análisis automático', size: 250,
      accessorFn: row => generateRunAutoAnalysis(row).title,
      filterVariant: 'select', filterSelectOptions: analysisOptions, filterFn: 'equals',
      Cell: ({ row }) => <div className="report-cell report-analysis-cell">
        {renderAnalysis ? renderAnalysis(row.original)
          : <RunAnalysisCell run={row.original} variant={variant} processKind="training" onRunSelect={onRunSelect} />}
      </div>,
    },
    ...extraColumns,
  ], [analysisOptions, extraColumns, isActive, modelOptions, onRunSelect, renderAnalysis, runOptions, variant]);

  const selectedIds = selection?.ids;
  const data = useMemo(() => onlySelected && selectedIds ? trainings.filter(training => selectedIds.includes(training.run_id)) : trainings,
    [onlySelected, selectedIds, trainings]);
  const rowSelection = useMemo<MRT_RowSelectionState>(
    () => Object.fromEntries((selectedIds ?? []).map(id => [id, true])), [selectedIds]);
  const available = selection?.maximum === undefined ? 0 : selection.maximum - selection.ids.length;

  const table = useMaterialReactTable({
    columns, data, localization: MRT_Localization_ES,
    getRowId: row => row.run_id,
    state: { columnFilters, globalFilter, pagination, rowSelection, expanded: renderDetailPanel ? true : {} },
    onColumnFiltersChange: updateFilters,
    onGlobalFilterChange: value => { setGlobalFilter(value ?? ''); setPagination(current => ({ ...current, pageIndex: 0 })); },
    onPaginationChange: setPagination,
    // Loading a TRAIN's children refreshes its counters (new data array); that must not send the user to page 1.
    autoResetPageIndex: false,
    initialState: {
      showColumnFilters: true, showGlobalFilter: true, density: 'compact',
      columnVisibility: { recall: false, specificity: false, f2: false, auc: false, 'mrt-row-expand': false },
      sorting: [{ id: 'run', desc: true }],
    },
    globalFilterFn: 'contains',
    enableColumnFilters: true, enableGlobalFilter: true, enableSorting: true, enableMultiSort: true,
    enableFacetedValues: true, enableColumnActions: false, enableDensityToggle: false, enableFullScreenToggle: false,
    enableColumnResizing: false, enableHiding: true, enableStickyHeader: false,
    columnFilterDisplayMode: 'subheader', positionGlobalFilter: 'left',
    muiSearchTextFieldProps: { placeholder: 'Buscar RUN, modelo, optimizer o UUID', sx: { minWidth: 300 }, variant: 'outlined', size: 'small' },
    muiPaginationProps: { rowsPerPageOptions: [TRAINING_RUNS_PAGE_SIZE, 14, 28, 50], showFirstButton: true, showLastButton: true },
    paginationDisplayMode: 'pages',
    enableRowSelection: selection
      ? row => selection.ids.includes(row.original.run_id) || (available > 0 && selection.canSelect(row.original))
      : false,
    enableMultiRowSelection: true, enableSelectAll: false,
    onRowSelectionChange: updater => {
      if (!selection) return;
      const next = typeof updater === 'function' ? updater(rowSelection) : updater;
      new Set([...Object.keys(next), ...selection.ids]).forEach(id => {
        if (Boolean(next[id]) !== selection.ids.includes(id)) selection.onChange(id, Boolean(next[id]));
      });
    },
    positionToolbarAlertBanner: 'none',
    renderDetailPanel: renderDetailPanel ? ({ row }) => renderDetailPanel(row.original) : undefined,
    // The derived pipeline stays visible under every TRAIN, as in the card layout.
    getRowCanExpand: () => Boolean(renderDetailPanel),
    enableExpandAll: false,
    muiDetailPanelProps: ({ row }) => ({ className: `trn-detail${isActive(row.original) ? ' trn-row--active' : ''}` }),
    muiTableBodyRowProps: ({ row }) => ({
      className: `trn-row${renderDetailPanel ? ' trn-row--with-detail' : ''}${isActive(row.original) ? ' trn-row--active' : ''}`,
      'aria-selected': selection ? row.getIsSelected() : undefined,
    }),
    muiTablePaperProps: { elevation: 0, className: 'trn-mrt' },
    renderTopToolbarCustomActions: () => <div className="trn-toolbar">
      {title}
      <button type="button" className="report-detail-button" aria-pressed={runFilter === ACTIVE_MODEL_FILTER}
        disabled={!activeTraining && runFilter !== ACTIVE_MODEL_FILTER} onClick={toggleActiveModel}
        title={activeTraining ? `Mostrar ${activeTraining.run_name?.trim() || activeTraining.run_id}` : 'No hay un modelo en Estado Activo'}>
        {runFilter === ACTIVE_MODEL_FILTER ? 'Mostrar todos los modelos' : activeTraining ? 'Buscar modelo activo' : 'Sin modelo activo'}
      </button>
      {selection ? <button type="button" className="report-detail-button" aria-pressed={onlySelected}
        disabled={!selection.ids.length && !onlySelected}
        onClick={() => { setOnlySelected(value => !value); setPagination(current => ({ ...current, pageIndex: 0 })); }}>
        {onlySelected ? 'Ver todos los TRAIN' : `Ver sólo seleccionados (${selection.ids.length})`}
      </button> : null}
    </div>,
  });

  return <ThemeProvider theme={inDialog ? dialogTheme : pageTheme}><MaterialReactTable table={table} /></ThemeProvider>;
}
