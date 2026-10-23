import { useLayoutEffect, useMemo, useRef, useState } from 'react';
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef, type MRT_PaginationState, type MRT_SortingState } from 'material-react-table';
import { MRT_Localization_ES } from 'material-react-table/locales/es';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import type { ConsensusEvidence } from '../../types/scientificReport';
import { CopyText } from './ComparisonPython';

type Sample = NonNullable<ConsensusEvidence['samples']>[number];
const runLabel = (index: number) => `RUN ${String.fromCharCode(65 + index)}`;
const shortSample = (sample: string) => /^[0-9a-f-]{36}$/i.test(sample) ? `${sample.slice(0, 8)}…` : sample.split('/').pop() ?? sample;
// MUI inherits the design-system font instead of Roboto.
const theme = createTheme({ typography: { fontFamily: 'inherit' } });
const score = (value: number) => value.toLocaleString('es-CL', { maximumFractionDigits: 4 });

const VISIBLE_ROWS = 10;

/**
 * Server-side page of consensus samples: the backend filters by category, sorts the whole filtered population and
 * pages it; the table adds column hiding, resizing and density, and the per-cell XAI action.
 * The body is exactly as tall as 10 rows (sticky header); it only scrolls when a larger page is chosen.
 */
export function ConsensusSamplesTable({ data, labels, pagination, onPagination, sorting, onSorting, loading, onExplain, explainBlocked }: {
  data: ConsensusEvidence; labels: Record<string, string>; pagination: MRT_PaginationState;
  onPagination: (next: MRT_PaginationState) => void; sorting: MRT_SortingState; onSorting: (next: MRT_SortingState) => void; loading?: boolean;
  onExplain?: (sample: string) => void; explainBlocked?: string | null;
}) {
  const runs = data.coverage?.length ?? 0;
  const columns = useMemo<MRT_ColumnDef<Sample>[]>(() => [
    { id: 'sample', header: 'Muestra', accessorKey: 'sample', size: 230,
      Cell: ({ row }) => <span className="scc-sample-id"><code title={row.original.sample}>{shortSample(row.original.sample)}</code><CopyText text={row.original.sample} label="Copiar muestra" iconOnly /></span> },
    { id: 'label', header: 'Clase real', accessorFn: row => row.label === 1 ? 'Parasitada' : 'No parasitada', size: 130 },
    { id: 'category', header: 'Categoría', accessorFn: row => labels[row.category] ?? row.category, size: 190 },
    ...Array.from({ length: runs }, (_, index): MRT_ColumnDef<Sample> => ({
      id: `run-${index}`, header: runLabel(index), size: 170, accessorFn: row => row.runs[index]?.score,
      Cell: ({ row }) => {
        const result = row.original.runs[index];
        return result ? <span className="scc-run-result" data-correct={result.correct}>{result.correct ? 'Acierto' : 'Error'} · clase {result.prediction}<small>score {score(result.score)}</small></span> : '—';
      },
    })),
    ...(onExplain ? [{ id: 'xai', header: 'XAI', size: 120, enableHiding: false, enableSorting: false,
      Cell: ({ row }) => <button type="button" className="ds-button" data-size="compact" disabled={Boolean(explainBlocked)}
        title={explainBlocked ?? 'Ver y generar la explicabilidad de esta célula en cada RUN'} onClick={() => onExplain(row.original.sample)}>Explicar</button> } as MRT_ColumnDef<Sample>] : []),
  ], [runs, labels, onExplain, explainBlocked]);
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
    columns, data: data.samples ?? [],
    localization: MRT_Localization_ES,
    manualPagination: true, manualSorting: true, rowCount: data.total ?? 0,
    state: { pagination, sorting, isLoading: Boolean(loading && !data.samples?.length), showProgressBars: Boolean(loading) },
    onPaginationChange: updater => onPagination(typeof updater === 'function' ? updater(pagination) : updater),
    onSortingChange: updater => onSorting(typeof updater === 'function' ? updater(sorting) : updater),
    enableSorting: true, enableMultiSort: false, enableSortingRemoval: true, enableStickyHeader: true,
    enableColumnFilters: false, enableGlobalFilter: false, enableColumnActions: false,
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
