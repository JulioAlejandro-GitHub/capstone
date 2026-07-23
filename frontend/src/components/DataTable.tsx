import { Fragment, type ReactNode } from 'react';

export interface Column<T> {
  header: string;
  render: (row: T) => ReactNode;
}

interface DataTableProps<T> {
  rows: T[];
  columns: Column<T>[];
  emptyText?: string;
  getRowKey?: (row: T, index: number) => string | number;
  expandedRowKey?: string | number | null;
  renderExpandedRow?: (row: T) => ReactNode;
  getRowClassName?: (row: T) => string | undefined;
  tableClassName?: string;
  expandedRowIdPrefix?: string;
}

export function DataTable<T>({ rows, columns, emptyText = 'Sin datos', getRowKey, expandedRowKey = null,
  renderExpandedRow, getRowClassName, tableClassName, expandedRowIdPrefix = 'expanded-row' }: DataTableProps<T>) {
  if (rows.length === 0) {
    return <div className="empty-state">{emptyText}</div>;
  }

  return (
    <div className="table-wrap">
      <table className={tableClassName}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.header}>{column.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const rowKey=getRowKey ? getRowKey(row,index) : index;
            const expanded=renderExpandedRow!==undefined&&expandedRowKey===rowKey;
            const panelId=`${expandedRowIdPrefix}-${String(rowKey)}`;
            return <Fragment key={rowKey}>
              <tr className={getRowClassName?.(row)} aria-expanded={renderExpandedRow?expanded:undefined} aria-controls={renderExpandedRow?panelId:undefined}>
                {columns.map((column) => <td key={column.header} data-label={column.header}>{column.render(row)}</td>)}
              </tr>
              {expanded?<tr className="expanded-table-row"><td colSpan={columns.length}><div id={panelId}>{renderExpandedRow(row)}</div></td></tr>:null}
            </Fragment>;
          })}
        </tbody>
      </table>
    </div>
  );
}
