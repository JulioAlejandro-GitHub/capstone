import { useMemo } from 'react';
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef, type MRT_PaginationState } from 'material-react-table';
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

/**
 * Server-side page of consensus samples (the backend filters by category and pages them); the table adds
 * column hiding, resizing and density, and the per-cell XAI action. No client recalculation or sorting.
 */
export function ConsensusSamplesTable({ data, labels, pagination, onPagination, loading, onExplain, explainBlocked }: {
  data: ConsensusEvidence; labels: Record<string, string>; pagination: MRT_PaginationState;
  onPagination: (next: MRT_PaginationState) => void; loading?: boolean;
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
    ...(onExplain ? [{ id: 'xai', header: 'XAI', size: 120, enableHiding: false,
      Cell: ({ row }) => <button type="button" className="ds-button" data-size="compact" disabled={Boolean(explainBlocked)}
        title={explainBlocked ?? 'Ver y generar la explicabilidad de esta célula en cada RUN'} onClick={() => onExplain(row.original.sample)}>Explicar</button> } as MRT_ColumnDef<Sample>] : []),
  ], [runs, labels, onExplain, explainBlocked]);
  const table = useMaterialReactTable({
    columns, data: data.samples ?? [],
    localization: MRT_Localization_ES,
    manualPagination: true, rowCount: data.total ?? 0,
    state: { pagination, isLoading: Boolean(loading && !data.samples?.length), showProgressBars: Boolean(loading) },
    onPaginationChange: updater => onPagination(typeof updater === 'function' ? updater(pagination) : updater),
    enableSorting: false, enableColumnFilters: false, enableGlobalFilter: false, enableColumnActions: false,
    enableColumnResizing: true, enableDensityToggle: true, enableFullScreenToggle: false, enableTopToolbar: true,
    initialState: { density: 'compact' },
    getRowId: row => row.sample,
    muiPaginationProps: { rowsPerPageOptions: [10, 25, 50, 100] },
    muiTablePaperProps: { elevation: 0, className: 'scc-mrt' },
    muiTableContainerProps: { sx: { maxHeight: '60vh' } },
    renderTopToolbarCustomActions: () => <strong className="scc-mrt-title">Muestras · {data.total ?? 0} resultados del filtro</strong>,
  });
  return <ThemeProvider theme={theme}><MaterialReactTable table={table} /></ThemeProvider>;
}
