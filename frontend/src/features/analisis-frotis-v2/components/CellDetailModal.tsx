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
    <div className="fixed inset-0 frotis-layer-modal flex items-center justify-center bg-frotis-overlay-base/70 backdrop-blur-xs p-frotis-component-padding select-none animate-in fade-in">
      <div className="bg-frotis-detail-surface text-frotis-text-inverse border-frotis border-frotis-border-inverse w-full max-w-2xl rounded-lg shadow-2xl overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="px-5 py-3.5 bg-frotis-detail-header border-b border-frotis-border-inverse flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h3 className="text-base font-bold text-frotis-text-inverse tracking-wide">
              Inspección Morfológica de Alta Resolución
            </h3>
            <span className="font-mono text-xs px-2 py-0.5 rounded-sm bg-frotis-secondary-dark/60 text-frotis-accent-soft border-frotis border-frotis-secondary-hover">
              Célula #{cell.id}
            </span>
          </div>
          <button
            aria-label="Cerrar"
            onClick={onClose}
            className="p-1 text-frotis-text-muted hover:text-frotis-text-inverse hover:bg-frotis-surface-inverse-raised rounded-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-frotis-panel-gap">
          {/* Left: High-Magnification View */}
          <div className="flex flex-col items-center">
            <div className="w-64 h-64 rounded-md overflow-hidden border-2 border-frotis-accent/50 shadow-lg relative bg-frotis-surface-inverse">
              <CellMicrograph
                cell={cell}
                size={256}
                isSelected={false}
                showIdBadge={false}
              />
              <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded-sm bg-frotis-overlay-base/70 text-frotis-caption font-mono text-frotis-text-inverse/90">
                100x Oil Immersion • Visor Full-Field
              </div>
            </div>

            {/* Navigation buttons */}
            <div className="flex items-center justify-between w-64 mt-3">
              <button
                onClick={onPrevious}
                className="flex items-center gap-1 px-3 py-1 bg-frotis-surface-inverse-raised hover:bg-frotis-surface-inverse-elevated text-xs text-frotis-border-strong rounded-sm transition-colors"
              >
                <ChevronLeft className="w-frotis-icon-size h-frotis-icon-size" /> Anterior
              </button>
              <button
                onClick={onNext}
                className="flex items-center gap-1 px-3 py-1 bg-frotis-surface-inverse-raised hover:bg-frotis-surface-inverse-elevated text-xs text-frotis-border-strong rounded-sm transition-colors"
              >
                Siguiente <ChevronRight className="w-frotis-icon-size h-frotis-icon-size" />
              </button>
            </div>
          </div>

          {/* Right: Detailed Morphology & Reclassification Controls */}
          <div className="flex flex-col justify-between text-xs space-y-4">
            <div>
              <div className="text-frotis-text-muted font-medium text-frotis-label uppercase tracking-wider mb-1">
                Clasificación Actual
              </div>
              <div className="text-lg font-bold text-frotis-accent-soft flex items-center justify-between">
                <span>{cell.name}</span>
                <span className="text-xs font-mono font-normal text-frotis-success-marker">
                  {(cell.confidence * 100).toFixed(1)}% Confianza AI
                </span>
              </div>
            </div>

            {/* Morphology Criteria */}
            <div className="space-y-2 bg-frotis-surface-inverse-raised/60 p-3 rounded-md border-frotis border-frotis-border-inverse/60">
              <div className="flex justify-between">
                <span className="text-frotis-text-muted">Diámetro celular:</span>
                <span className="font-mono">{cell.diameterUm || 18.5} µm</span>
              </div>
              <div className="flex justify-between">
                <span className="text-frotis-text-muted">Patrón de cromatina:</span>
                <span className="text-right text-frotis-border">
                  {cell.chromatinPattern || "Fina con 1 nucleolo"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-frotis-text-muted">Granulaciones:</span>
                <span className="text-right text-frotis-border">
                  {cell.granules || "Abundantes azurófilas primarias"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-frotis-text-muted">Relación N:C:</span>
                <span className="font-mono">Elevada (~0.80)</span>
              </div>
            </div>

            {/* Reclassification Selector */}
            <div>
              <label className="block text-frotis-border-strong font-medium mb-1">
                Modificar Reclasificación:
              </label>
              <select
                value={cell.category}
                onChange={(e) => onReclassify(e.target.value)}
                className="w-full bg-frotis-surface-inverse-raised text-frotis-text-inverse border-frotis border-frotis-border-inverse-strong rounded-md px-3 py-1.5 focus:outline-none focus:border-frotis-accent"
              >
                {availableCategories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2 pt-2 border-t border-frotis-border-inverse">
              <button
                onClick={onToggleFlag}
                className={`flex-1 flex items-center justify-center gap-frotis-control-gap py-1.5 rounded-md font-medium transition-colors ${
                  cell.flagged
                    ? "bg-frotis-error text-frotis-text-inverse"
                    : "bg-frotis-surface-inverse-raised hover:bg-frotis-surface-inverse-elevated text-frotis-border"
                }`}
              >
                <Flag className="w-frotis-icon-size-sm h-frotis-icon-size-sm" />
                {cell.flagged
                  ? "Marcada para revisión"
                  : "Marcar para revisión"}
              </button>
              <button
                aria-label="Cerrar"
                onClick={onClose}
                className="px-4 py-1.5 bg-frotis-secondary hover:bg-frotis-accent text-frotis-text-inverse font-medium rounded-md transition-colors"
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
