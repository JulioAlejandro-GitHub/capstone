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
      <div className="h-9 px-4 bg-slate-900 text-white flex items-center justify-between text-xs z-10 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-indigo-300">
            {isAnalysisArea
              ? "ÁREA DE ANÁLISIS AUTOMÁTICO"
              : "REVISIÓN DE CAMPO COMPLETO (FULL FIELD)"}
          </span>
          <span className="text-slate-400">|</span>
          <span className="text-slate-300">
            Escaneado continuo de resolución óptica total (2.27 cm²)
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowHeatmap(!showHeatmap)}
            className={`flex items-center gap-1.5 px-2 py-0.5 rounded-xs transition-colors ${
              showHeatmap
                ? "bg-amber-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            <Flame className="w-3.5 h-3.5" />
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
          <div className="absolute inset-0 pointer-events-none bg-gradient-radial from-amber-500/25 via-indigo-600/15 to-transparent mix-blend-multiply flex items-center justify-center">
            <div className="bg-slate-900/80 text-white px-3 py-1.5 rounded-full text-xs font-mono shadow-lg flex items-center gap-2">
              <Flame className="w-4 h-4 text-amber-400" />
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
