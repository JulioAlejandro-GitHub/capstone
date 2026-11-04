import React from "react";
import { CellItem } from "../types/visor";
import { CellMicrograph } from "./CellMicrograph";
import {
  X,
  ChevronLeft,
  ChevronRight,
  Flag,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sparkles,
} from "lucide-react";

interface CellDetailModalProps {
  cell: CellItem;
  onClose: () => void;
  onPrevious: () => void;
  onNext: () => void;
  onReclassify: (newCat: string) => void;
  onToggleFlag: () => void;
  availableCategories: string[];
}

export const CellDetailModal: React.FC<CellDetailModalProps> = ({
  cell,
  onClose,
  onPrevious,
  onNext,
  onReclassify,
  onToggleFlag,
  availableCategories,
}) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 select-none animate-in fade-in">
      <div className="bg-[#24272c] text-white border border-slate-700 w-full max-w-2xl rounded-lg shadow-2xl overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="px-5 py-3.5 bg-[#1e2024] border-b border-slate-700 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h3 className="text-base font-bold text-white tracking-wide">
              Inspección Morfológica de Alta Resolución
            </h3>
            <span className="font-mono text-xs px-2 py-0.5 rounded-sm bg-indigo-900/60 text-indigo-300 border border-indigo-700">
              Célula #{cell.id}
            </span>
          </div>
          <button
            aria-label="Cerrar"
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-6">
          {/* Left: High-Magnification View */}
          <div className="flex flex-col items-center">
            <div className="w-64 h-64 rounded-md overflow-hidden border-2 border-indigo-500/50 shadow-lg relative bg-slate-900">
              <CellMicrograph
                cell={cell}
                size={256}
                isSelected={false}
                showIdBadge={false}
              />
              <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded-sm bg-black/70 text-[10px] font-mono text-white/90">
                100x Oil Immersion • Visor Full-Field
              </div>
            </div>

            {/* Navigation buttons */}
            <div className="flex items-center justify-between w-64 mt-3">
              <button
                onClick={onPrevious}
                className="flex items-center gap-1 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 rounded-sm transition-colors"
              >
                <ChevronLeft className="w-4 h-4" /> Anterior
              </button>
              <button
                onClick={onNext}
                className="flex items-center gap-1 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 rounded-sm transition-colors"
              >
                Siguiente <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Right: Detailed Morphology & Reclassification Controls */}
          <div className="flex flex-col justify-between text-xs space-y-4">
            <div>
              <div className="text-slate-400 font-medium text-[11px] uppercase tracking-wider mb-1">
                Clasificación Actual
              </div>
              <div className="text-lg font-bold text-indigo-300 flex items-center justify-between">
                <span>{cell.name}</span>
                <span className="text-xs font-mono font-normal text-emerald-400">
                  {(cell.confidence * 100).toFixed(1)}% Confianza AI
                </span>
              </div>
            </div>

            {/* Morphology Criteria */}
            <div className="space-y-2 bg-slate-800/60 p-3 rounded-md border border-slate-700/60">
              <div className="flex justify-between">
                <span className="text-slate-400">Diámetro celular:</span>
                <span className="font-mono">{cell.diameterUm || 18.5} µm</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Patrón de cromatina:</span>
                <span className="text-right text-slate-200">
                  {cell.chromatinPattern || "Fina con 1 nucleolo"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Granulaciones:</span>
                <span className="text-right text-slate-200">
                  {cell.granules || "Abundantes azurófilas primarias"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Relación N:C:</span>
                <span className="font-mono">Elevada (~0.80)</span>
              </div>
            </div>

            {/* Reclassification Selector */}
            <div>
              <label className="block text-slate-300 font-medium mb-1">
                Modificar Reclasificación:
              </label>
              <select
                value={cell.category}
                onChange={(e) => onReclassify(e.target.value)}
                className="w-full bg-slate-800 text-white border border-slate-600 rounded-md px-3 py-1.5 focus:outline-none focus:border-indigo-500"
              >
                {availableCategories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2 pt-2 border-t border-slate-700">
              <button
                onClick={onToggleFlag}
                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md font-medium transition-colors ${
                  cell.flagged
                    ? "bg-rose-600 text-white"
                    : "bg-slate-800 hover:bg-slate-700 text-slate-200"
                }`}
              >
                <Flag className="w-3.5 h-3.5" />
                {cell.flagged
                  ? "Marcada para revisión"
                  : "Marcar para revisión"}
              </button>
              <button
                aria-label="Cerrar"
                onClick={onClose}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-md transition-colors"
              >
                Guardar y Cerrar
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
