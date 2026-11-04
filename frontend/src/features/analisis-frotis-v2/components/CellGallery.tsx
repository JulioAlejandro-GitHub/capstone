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
    <div className="flex-1 flex flex-col h-full bg-[#303338] text-white overflow-hidden select-none border-r border-slate-700">
      {/* Top Category Stats & Header Bar */}
      <div className="px-4 py-2.5 bg-[#282b30] border-b border-slate-700 flex items-center justify-between gap-4">
        {/* Category Title */}
        <div>
          <h2 className="text-base font-semibold tracking-wide text-white flex items-center gap-2">
            <span>{selectedCategory}</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-300 font-normal">
              {displayedCells.length} visibles
            </span>
          </h2>
        </div>

        {/* Right Stats (Matching Visor screen: Total count / % & Abnormal count / %) */}
        <div className="flex items-center gap-6 text-xs">
          <div className="text-right">
            <span className="text-slate-400 mr-2 text-[11px]">
              Total count / percentage
            </span>
            <span className="font-mono font-semibold text-white">
              {categoryStats
                ? `${categoryStats.count} / ${categoryStats.percentage}%`
                : `${cells.length} / --`}
            </span>
          </div>

          <div className="text-right pl-4 border-l border-slate-700">
            <span className="text-slate-400 mr-2 text-[11px]">
              Total abnormal count / percentage
            </span>
            <span className="font-mono font-semibold text-amber-400">
              {categoryStats?.abnormalCount
                ? `${categoryStats.abnormalCount} / 100%`
                : "0 / 0%"}
            </span>
          </div>

          {/* Grid density selector (4, 6, 8 columns) */}
          <div className="flex items-center bg-slate-800 rounded-sm border border-slate-700 p-0.5 ml-2">
            <button
              onClick={() => setColumns(4)}
              className={`px-2 py-0.5 text-xs font-mono rounded-xs ${
                columns === 4
                  ? "bg-indigo-600 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
              title="Celdas grandes (4 cols)"
            >
              4
            </button>
            <button
              onClick={() => setColumns(6)}
              className={`px-2 py-0.5 text-xs font-mono rounded-xs ${
                columns === 6
                  ? "bg-indigo-600 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
              title="Estándar (6 cols - Visor)"
            >
              6
            </button>
            <button
              onClick={() => setColumns(8)}
              className={`px-2 py-0.5 text-xs font-mono rounded-xs ${
                columns === 8
                  ? "bg-indigo-600 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
              title="Compacto (8 cols)"
            >
              8
            </button>
          </div>
        </div>
      </div>

      {/* Gallery Toolbar for Reclassification & Quick Actions */}
      <div className="px-4 py-1.5 bg-[#23262a] border-b border-slate-800 flex items-center justify-between text-xs text-slate-300">
        <div className="flex items-center gap-3">
          <span className="text-slate-400 text-[11px]">
            Botonera morfológica digital: haz clic para localizar en frotis o
            doble clic para ampliar.
          </span>
        </div>

        {/* Reclassify shortcut for selected cell */}
        {selectedCellId && (
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-indigo-300">
              Reclasificar #{selectedCellId}:
            </span>
            <select
              value={selectedCategory}
              onChange={(e) => onReclassifyCell(selectedCellId, e.target.value)}
              className="bg-slate-800 text-white border border-slate-600 rounded-xs px-2 py-0.5 text-xs focus:outline-none focus:border-indigo-500"
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
      <div className="flex-1 overflow-y-auto p-2 custom-scrollbar bg-[#2d3035]">
        <div
          className={`grid gap-1.5 ${
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
                  className="absolute bottom-1 left-1 opacity-0 group-hover:opacity-100 bg-slate-900/80 hover:bg-indigo-600 text-white p-1 rounded-xs transition-opacity shadow-sm z-20"
                  title="Cambiar tipo de célula"
                >
                  <ArrowRightLeft className="w-2.5 h-2.5" />
                </button>

                {/* Inline Reclassify Popover */}
                {reclassifyCellId === cell.id && (
                  <div
                    onClick={(e) => e.stopPropagation()}
                    className="absolute top-full left-0 mt-1 w-44 bg-slate-900 text-slate-200 border border-slate-700 rounded-md shadow-xl py-1 z-50 text-xs animate-in fade-in"
                  >
                    <div className="px-2 py-1 text-[10px] text-slate-400 font-semibold uppercase border-b border-slate-800">
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
                            className="w-full text-left px-2 py-1 hover:bg-indigo-600 hover:text-white transition-colors truncate"
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
          <div className="h-64 flex flex-col items-center justify-center text-slate-400">
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
