import React, { useState } from "react";
import { CellItem, DifferentialCategory } from "../types/visor";
import { CellMicrograph } from "./CellMicrograph";
import {
  ZoomIn,
  ZoomOut,
  SlidersHorizontal,
  Bookmark,
  CheckSquare,
  ArrowRightLeft,
  ChevronDown,
  Info,
} from "lucide-react";

interface CellGalleryProps {
  selectedCategory: string;
  categoryStats?: DifferentialCategory;
  cells: CellItem[];
  selectedCellId: number | null;
  onSelectCell: (cell: CellItem) => void;
  onInspectCell: (cell: CellItem) => void;
  onReclassifyCell: (cellId: number, newCategory: string) => void;
  availableCategories: string[];
}

export const CellGallery: React.FC<CellGalleryProps> = ({
  selectedCategory,
  categoryStats,
  cells,
  selectedCellId,
  onSelectCell,
  onInspectCell,
  onReclassifyCell,
  availableCategories,
}) => {
  const [columns, setColumns] = useState<6 | 4 | 8>(6);
  const [reclassifyCellId, setReclassifyCellId] = useState<number | null>(null);
  const [filterAbnormal, setFilterAbnormal] = useState(false);

  const displayedCells = filterAbnormal
    ? cells.filter((c) => c.abnormal || c.flagged)
    : cells;

  return (
    <div className="flex-1 flex flex-col h-full bg-frotis-gallery-surface text-frotis-text-inverse overflow-hidden select-none border-r border-frotis-border-inverse">
      {/* Top Category Stats & Header Bar */}
      <div className="px-4 py-2.5 bg-frotis-gallery-header border-b border-frotis-border-inverse flex items-center justify-between gap-4">
        {/* Category Title */}
        <div>
          <h2 className="text-base font-semibold tracking-wide text-frotis-text-inverse flex items-center gap-2">
            <span>{selectedCategory}</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-frotis-surface-inverse-elevated text-frotis-border-strong font-normal">
              {displayedCells.length} visibles
            </span>
          </h2>
        </div>

        {/* Right Stats (Matching Visor screen: Total count / % & Abnormal count / %) */}
        <div className="flex items-center gap-frotis-panel-gap text-xs">
          <div className="text-right">
            <span className="text-frotis-text-muted mr-2 text-frotis-label">
              Total count / percentage
            </span>
            <span className="font-mono font-semibold text-frotis-text-inverse">
              {categoryStats
                ? `${categoryStats.count} / ${categoryStats.percentage}%`
                : `${cells.length} / --`}
            </span>
          </div>

          <div className="text-right pl-4 border-l border-frotis-border-inverse">
            <span className="text-frotis-text-muted mr-2 text-frotis-label">
              Total abnormal count / percentage
            </span>
            <span className="font-mono font-semibold text-frotis-warning-marker">
              {categoryStats?.abnormalCount
                ? `${categoryStats.abnormalCount} / 100%`
                : "0 / 0%"}
            </span>
          </div>

          {/* Grid density selector (4, 6, 8 columns) */}
          <div className="flex items-center bg-frotis-surface-inverse-raised rounded-sm border-frotis border-frotis-border-inverse p-0.5 ml-2">
            <button
              onClick={() => setColumns(4)}
              className={`px-2 py-0.5 text-xs font-mono rounded-xs ${
                columns === 4
                  ? "bg-frotis-secondary text-frotis-text-inverse"
                  : "text-frotis-text-muted hover:text-frotis-text-inverse"
              }`}
              title="Celdas grandes (4 cols)"
            >
              4
            </button>
            <button
              onClick={() => setColumns(6)}
              className={`px-2 py-0.5 text-xs font-mono rounded-xs ${
                columns === 6
                  ? "bg-frotis-secondary text-frotis-text-inverse"
                  : "text-frotis-text-muted hover:text-frotis-text-inverse"
              }`}
              title="Estándar (6 cols - Visor)"
            >
              6
            </button>
            <button
              onClick={() => setColumns(8)}
              className={`px-2 py-0.5 text-xs font-mono rounded-xs ${
                columns === 8
                  ? "bg-frotis-secondary text-frotis-text-inverse"
                  : "text-frotis-text-muted hover:text-frotis-text-inverse"
              }`}
              title="Compacto (8 cols)"
            >
              8
            </button>
          </div>
        </div>
      </div>

      {/* Gallery Toolbar for Reclassification & Quick Actions */}
      <div className="px-4 py-1.5 bg-frotis-gallery-toolbar border-b border-frotis-border-inverse-deep flex items-center justify-between text-xs text-frotis-border-strong">
        <div className="flex items-center gap-3">
          <span className="text-frotis-text-muted text-frotis-label">
            Botonera morfológica digital: haz clic para localizar en frotis o
            doble clic para ampliar.
          </span>
        </div>

        {/* Reclassify shortcut for selected cell */}
        {selectedCellId && (
          <div className="flex items-center gap-2">
            <span className="text-frotis-label text-frotis-accent-soft">
              Reclasificar #{selectedCellId}:
            </span>
            <select
              value={selectedCategory}
              onChange={(e) => onReclassifyCell(selectedCellId, e.target.value)}
              className="bg-frotis-surface-inverse-raised text-frotis-text-inverse border-frotis border-frotis-border-inverse-strong rounded-xs px-2 py-0.5 text-xs focus:outline-none focus:border-frotis-accent"
            >
              {availableCategories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Main Grid View ("Botonera") */}
      <div className="flex-1 overflow-y-auto p-2 custom-scrollbar bg-frotis-gallery-canvas">
        <div
          className={`grid gap-frotis-control-gap ${
            columns === 4
              ? "grid-cols-4"
              : columns === 6
                ? "grid-cols-6"
                : "grid-cols-8"
          }`}
        >
          {displayedCells.map((cell) => {
            const isSelected = selectedCellId === cell.id;
            return (
              <div key={cell.id} className="relative group">
                <CellMicrograph
                  cell={cell}
                  isSelected={isSelected}
                  onClick={() => onSelectCell(cell)}
                  onDoubleClick={() => onInspectCell(cell)}
                />

                {/* Quick Reclassify button visible on hover */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setReclassifyCellId(
                      reclassifyCellId === cell.id ? null : cell.id,
                    );
                  }}
                  className="absolute bottom-1 left-1 opacity-0 group-hover:opacity-100 bg-frotis-surface-inverse/80 hover:bg-frotis-secondary text-frotis-text-inverse p-1 rounded-xs transition-opacity shadow-sm frotis-layer-toolbar"
                  title="Cambiar tipo de célula"
                >
                  <ArrowRightLeft className="w-2.5 h-2.5" />
                </button>

                {/* Inline Reclassify Popover */}
                {reclassifyCellId === cell.id && (
                  <div
                    onClick={(e) => e.stopPropagation()}
                    className="absolute top-full left-0 mt-1 w-44 bg-frotis-surface-inverse text-frotis-border border-frotis border-frotis-border-inverse rounded-md shadow-xl py-1 frotis-layer-popover text-xs animate-in fade-in"
                  >
                    <div className="px-2 py-1 text-frotis-caption text-frotis-text-muted font-semibold uppercase border-b border-frotis-border-inverse-deep">
                      Reclasificar #{cell.id} a:
                    </div>
                    <div className="max-h-40 overflow-y-auto custom-scrollbar">
                      {availableCategories
                        .filter((c) => c !== cell.category)
                        .map((cat) => (
                          <button
                            key={cat}
                            onClick={() => {
                              onReclassifyCell(cell.id, cat);
                              setReclassifyCellId(null);
                            }}
                            className="w-full text-left px-2 py-1 hover:bg-frotis-secondary hover:text-frotis-text-inverse transition-colors truncate"
                          >
                            {cat}
                          </button>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {displayedCells.length === 0 && (
          <div className="h-64 flex flex-col items-center justify-center text-frotis-text-muted">
            <Info className="w-8 h-8 mb-2 stroke-[1.5]" />
            <p className="text-sm">
              No hay células encontradas con los filtros actuales
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
