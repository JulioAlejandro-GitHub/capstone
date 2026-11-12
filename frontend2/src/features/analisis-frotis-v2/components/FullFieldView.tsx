import React, { useState } from "react";
import { ClinicalCase, CellItem, ImageAdjustments } from "../types/visor";
import { SlideViewer } from "./SlideViewer";
import { Layers, Flame, Eye, Sparkles } from "lucide-react";

interface FullFieldViewProps {
  activeCase: ClinicalCase;
  cells: CellItem[];
  selectedCellId: number | null;
  onSelectCell: (cell: CellItem) => void;
  isAnalysisArea?: boolean;
  imageAdjustments?: ImageAdjustments;
  onChangeAdjustments?: (adjustments: ImageAdjustments) => void;
}

export const FullFieldView: React.FC<FullFieldViewProps> = ({
  activeCase,
  cells,
  selectedCellId,
  onSelectCell,
  isAnalysisArea = false,
  imageAdjustments,
  onChangeAdjustments,
}) => {
  const [showHeatmap, setShowHeatmap] = useState(isAnalysisArea);

  return (
    <div className="flex-1 flex flex-col h-full relative select-none">
      {/* Subheader banner */}
      <div className="h-frotis-toolbar-height px-4 bg-frotis-surface-inverse text-frotis-text-inverse flex items-center justify-between text-xs frotis-layer-overlay border-b border-frotis-border-inverse">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-frotis-accent-soft">
            {isAnalysisArea
              ? "ÁREA DE ANÁLISIS AUTOMÁTICO"
              : "REVISIÓN DE CAMPO COMPLETO (FULL FIELD)"}
          </span>
          <span className="text-frotis-text-muted">|</span>
          <span className="text-frotis-border-strong">
            Escaneado continuo de resolución óptica total (2.27 cm²)
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowHeatmap(!showHeatmap)}
            className={`flex items-center gap-frotis-control-gap px-2 py-0.5 rounded-xs transition-colors ${
              showHeatmap
                ? "bg-frotis-warning text-frotis-text-inverse"
                : "bg-frotis-surface-inverse-raised text-frotis-border-strong hover:bg-frotis-surface-inverse-elevated"
            }`}
          >
            <Flame className="w-frotis-icon-size-sm h-frotis-icon-size-sm" />
            <span>Mapa de Densidad Celular</span>
          </button>
        </div>
      </div>

      {/* Main Slide Viewer Canvas */}
      <div className="flex-1 relative">
        <SlideViewer
          cells={cells}
          selectedCellId={selectedCellId}
          onSelectCell={onSelectCell}
          onChangeAdjustments={onChangeAdjustments}
          imageAdjustments={
            imageAdjustments ?? {
              brightness: 100,
              contrast: 100,
              gamma: 1.0,
              saturation: 100,
              preset: 1,
            }
          }
          createdDate={activeCase.createdDate}
          scanSizeCm2={activeCase.scanSizeCm2}
        />

        {/* Heatmap overlay if enabled */}
        {showHeatmap && (
          <div className="absolute inset-0 pointer-events-none bg-gradient-radial from-frotis-warning-accent/25 via-frotis-secondary/15 to-transparent mix-blend-multiply flex items-center justify-center">
            <div className="bg-frotis-surface-inverse/80 text-frotis-text-inverse px-3 py-1.5 rounded-full text-xs font-mono shadow-lg flex items-center gap-2">
              <Flame className="w-frotis-icon-size h-frotis-icon-size text-frotis-warning-marker" />
              <span>
                Zona Óptima de Recuento Monocapa: Concentración 48 células / HPF
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
