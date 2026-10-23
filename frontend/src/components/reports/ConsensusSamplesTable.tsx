import { useLayoutEffect, useMemo, useRef, useState } from 'react';
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef, type MRT_PaginationState, type MRT_SortingState, type MRT_ColumnFiltersState } from 'material-react-table';
import { MRT_Localization_ES } from 'material-react-table/locales/es';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import type { ConsensusEvidence } from '../../types/scientificReport';
import { CopyText } from './ComparisonPython';
import { useScientificArtifact } from '../../hooks/useScientificArtifact';

type Sample = NonNullable<ConsensusEvidence['samples']>[number];
const runLabel = (index: number) => `RUN ${String.fromCharCode(65 + index)}`;
const shortSample = (sample: string) => /^[0-9a-f-]{36}$/i.test(sample) ? `${sample.slice(0, 8)}…` : sample.split('/').pop() ?? sample;
// MUI inherits the design-system font instead of Roboto.
const theme = createTheme({ typography: { fontFamily: 'inherit' } });
const score = (value: number) => value.toLocaleString('es-CL', { maximumFractionDigits: 4 });

const VISIBLE_ROWS = 10;

type Source = NonNullable<ConsensusEvidence['sources']>[number];
// Original cell served under the EVALUATE lineage of the first RUN that has one; opens the cell's «Vista ampliada».
function SampleThumbnail({ sample, source, datasource, onOpen }: { sample: string; source: Source; datasource?: string; onOpen?: (sample: string) => void }) {
  const resource = useScientificArtifact(source ? { source: 'dataset_sample', trainingRunId: source.training_run_id, datasetVersionId: source.dataset_version_id,
    sampleId: sample, attemptId: source.attempt_id } : undefined, datasource, Boolean(source));
  const image = resource.url ? <img className="report-scientific-image" src={resource.url} alt={`Célula original ${sample}`} />
    : <small className="scc-meta">{resource.loading ? 'Cargando…' : source ? 'Sin imagen' : 'Sin linaje'}</small>;
  return <div className="xai-image-frame scc-sample-thumb">
    {onOpen ? <button type="button" className="xai-image-button" onClick={() => onOpen(sample)} aria-label={`Ver célula ${sample} y su explicabilidad`}
      title="Vista ampliada: célula original y explicabilidad por RUN">{image}</button> : image}
  </div>;
}

/**
 * Server-side page of consensus samples: the column filters (sample, real class, category, score range per RUN) are
 * sent to the backend, which filters and sorts the whole population before paging; the table adds column hiding,
 * resizing and density, and the per-cell XAI action.
 * The body is exactly as tall as 10 rows (sticky header); it only scrolls when a larger page is chosen.
 */
export function ConsensusSamplesTable({
data, labels, pagination, onPagination, sorting, onSorting, columnFilters, onColumnFilters, loading, datasource, onExplain}: {
  data: ConsensusEvidence; labels: Record<string, string>; pagination: MRT_PaginationState;
  onPagination: (next: MRT_PaginationState) => void; sorting: MRT_SortingState; onSorting: (next: MRT_SortingState) => void;
  columnFilters: MRT_ColumnFiltersState; onColumnFilters: (next: MRT_ColumnFiltersState) => void;
  loading?: boolean; datasource?: string; onExplain?: (sample: string) => void;
}) {
  const runs = data.coverage?.length ?? 0;
  const source = data.sources?.find(Boolean) ?? null;
  const columns = useMemo<MRT_ColumnDef<Sample>[]>(() => [
    { id: 'sample', header: 'Muestra', accessorKey: 'sample', size: 230,
      Cell: ({ row }) => <span className="scc-sample-id"><code title={row.original.sample}>{shortSample(row.original.sample)}</code><CopyText text={row.original.sample} label="Copiar muestra" iconOnly /></span> },
    // Filter values are what the backend expects: label 0/1 and the category key ('all' is the empty filter).
    { id: 'label', header: 'Clase real', accessorFn: row => row.label === 1 ? 'Parasitada' : 'No parasitada', size: 150,
      filterVariant: 'select', filterSelectOptions: [{ text: 'Parasitada', value: '1' }, { text: 'No parasitada', value: '0' }] },
    { id: 'category', header: 'Categoría', accessorFn: row => labels[row.category] ?? row.category, size: 210,
      filterVariant: 'select', filterSelectOptions: Object.entries(labels).filter(([key]) => key !== 'all').map(([value, text]) => ({ text, value })) },
    ...Array.from({ length: runs }, (_, index): MRT_ColumnDef<Sample> => ({
      id: `run-${index}`, header: runLabel(index), size: 190, accessorFn: row => row.runs[index]?.score ?? null,
      Cell: ({ row }) => {
        const result = row.original.runs[index];
        return result ? <span className="scc-run-result" data-correct={result.correct}>{result.correct ? 'Acierto' : 'Error'} · clase {result.prediction}<small>score {score(result.score)}</small></span> : '—';
      },
      // Score range over the whole population: fixed [0, 1] bounds instead of the faceted bounds of the current page.
      filterVariant: 'range-slider', muiFilterSliderProps: { min: 0, max: 1, step: 0.01, valueLabelDisplay: 'auto' },
    })),
    { id: 'xai', header: 'XAI', size: 110, enableHiding: false, enableSorting: false, enableColumnFilter: false,
      Cell: ({ row }) => <SampleThumbnail sample={row.original.sample} source={source} datasource={datasource} onOpen={onExplain} /> },
  ], [runs, labels, source, datasource, onExplain]);
  const container = useRef<HTMLDivElement>(null);
  const [maxHeight, setMaxHeight] = useState<number | undefined>(undefined);
  const rows = data.samples?.length ?? 0;
  useLayoutEffect(() => {
    const body = container.current?.querySelectorAll('tbody tr');
    if (!body || rows <= VISIBLE_ROWS) { setMaxHeight(undefined); return; }
    const last = body[VISIBLE_ROWS - 1] as HTMLElement | undefined;
    const head = container.current?.querySelector('thead') as HTMLElement | null;
    if (last && head) setMaxHeight(head.offsetHeight + last.offsetTop + last.offsetHeight - (body[0] as HTMLElement).offsetTop);
  }, [rows, data.samples]);
  const table = useMaterialReactTable({
    columns, data: data.samples ?? [], localization: MRT_Localization_ES,
    manualPagination: true, manualSorting: true, manualFiltering: true, rowCount: data.total ?? 0,
    state: { pagination, sorting, columnFilters, isLoading: Boolean(loading && !data.samples?.length), showProgressBars: Boolean(loading) },
    onPaginationChange: updater => onPagination(typeof updater === 'function' ? updater(pagination) : updater),
    onSortingChange: updater => onSorting(typeof updater === 'function' ? updater(sorting) : updater),
    onColumnFiltersChange: updater => onColumnFilters(typeof updater === 'function' ? updater(columnFilters) : updater),
    enableSorting: true, enableMultiSort: false, enableSortingRemoval: true, enableStickyHeader: true,
    enableColumnFilters: true, enableGlobalFilter: false, enableColumnActions: false, enableFacetedValues: false,
    enableColumnResizing: true, enableDensityToggle: true, enableFullScreenToggle: false, enableTopToolbar: true,
    initialState: { density: 'compact' },
    getRowId: row => row.sample,
    muiPaginationProps: { rowsPerPageOptions: [VISIBLE_ROWS, 25, 50, 100] },
    muiTablePaperProps: { elevation: 0, className: 'scc-mrt' },
    muiTableContainerProps: { ref: container, sx: { maxHeight: maxHeight ?? 'none' } },
    renderTopToolbarCustomActions: () => <strong className="scc-mrt-title">Muestras · {data.total ?? 0} resultados del filtro</strong>,
  });
  return <ThemeProvider theme={theme}><MaterialReactTable table={table} /></ThemeProvider>;
}
