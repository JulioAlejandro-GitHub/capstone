import React, { useState } from "react";
import {
  WorkflowTab,
  ViewLayoutMode,
  ClinicalCase,
  CaseStatus,
  ImageAdjustments,
} from "../types/visor";
import { ImageAdjustmentsPopover } from "./ImageAdjustmentsPopover";
import {
  Share2,
  FolderOpen,
  Sliders,
  Settings,
  X,
  Edit2,
  CheckCircle2,
  AlertCircle,
  FileCode,
  LayoutGrid,
  Columns,
  Maximize2,
  Sun,
  Contrast,
  ChevronDown,
} from "lucide-react";

interface HeaderProps {
  currentTab: WorkflowTab;
  onTabChange: (tab: WorkflowTab) => void;
  layoutMode: ViewLayoutMode;
  onLayoutModeChange: (mode: ViewLayoutMode) => void;
  activeCase: ClinicalCase;
  availableCases: ClinicalCase[];
  onSelectCase: (c: ClinicalCase) => void;
  imageAdjustments: ImageAdjustments;
  onChangeAdjustments: (adj: ImageAdjustments) => void;
  onOpenExport: () => void;
  onOpenStandaloneHtml: () => void;
  onStatusChange: (status: CaseStatus) => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onTabChange,
  layoutMode,
  onLayoutModeChange,
  activeCase,
  availableCases,
  onSelectCase,
  imageAdjustments,
  onChangeAdjustments,
  onOpenExport,
  onOpenStandaloneHtml,
  onStatusChange,
}) => {
  const [showCaseDropdown, setShowCaseDropdown] = useState(false);
  const [showStatusDropdown, setShowStatusDropdown] = useState(false);
  const [showPresetMenu, setShowPresetMenu] = useState(false);

  const tabs: WorkflowTab[] = [
    "FULL FIELD REVIEW",
    "SPECIMEN QUALITY",
    "ANALYSIS AREA",
    "REVIEW CELLS",
    "REPORT",
  ];

  const statuses: { label: CaseStatus; color: string }[] = [
    { label: "Reviewing", color: "bg-amber-400" },
    { label: "Flagged", color: "bg-rose-500" },
    { label: "Approved", color: "bg-emerald-500" },
    { label: "Signed-off", color: "bg-indigo-500" },
  ];

  const currentStatusObj =
    statuses.find((s) => s.label === activeCase.status) || statuses[0];

  return (
    <header className="w-full bg-white border-b border-slate-200 shadow-xs z-30 select-none">
      {/* Top Main Bar */}
      <div className="h-14 px-4 flex items-center justify-between gap-3">
        {/* Left: Visor Logo, Tool Icons, and Active Case Tab */}
        <div className="flex items-center gap-3">
          {/* Visor Logo */}
          <div className="flex items-center gap-2 pr-2 border-r border-slate-200">
            <div className="w-8 h-8 rounded-md bg-[#4D58A4] flex items-center justify-center text-white shadow-xs">
              <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current">
                <path d="M12 2L4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3zm0 4.5c1.93 0 3.5 1.57 3.5 3.5 0 1.27-.68 2.37-1.7 2.98L15 16h-2v-2h-2v2H9l1.2-3.02C9.18 12.37 8.5 11.27 8.5 10c0-1.93 1.57-3.5 3.5-3.5z" />
              </svg>
            </div>
            <span className="text-xl font-bold tracking-tight text-slate-800">
              Visor
            </span>
          </div>

          {/* Quick Utility Icons */}
          <div className="flex items-center gap-0.5 text-slate-500">
            <button
              onClick={onOpenExport}
              title="Compartir / Exportar reporte o datos"
              className="p-1.5 hover:text-slate-900 hover:bg-slate-100 rounded-md transition-colors"
            >
              <Share2 className="w-4 h-4" />
            </button>
            <div className="relative">
              <button
                onClick={() => setShowCaseDropdown(!showCaseDropdown)}
                title="Abrir o cambiar caso clínico"
                className="p-1.5 hover:text-slate-900 hover:bg-slate-100 rounded-md transition-colors"
              >
                <FolderOpen className="w-4 h-4" />
              </button>

              {/* Case switcher dropdown */}
              {showCaseDropdown && (
                <div className="absolute top-full left-0 mt-1 w-72 bg-white rounded-md shadow-lg border border-slate-200 py-1 z-50 animate-in fade-in slide-in-from-top-1">
                  <div className="px-3 py-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                    Casos Hematológicos Disponibles
                  </div>
                  {availableCases.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => {
                        onSelectCase(c);
                        setShowCaseDropdown(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-50 flex flex-col gap-0.5 ${
                        c.id === activeCase.id
                          ? "bg-indigo-50/60 font-semibold text-indigo-700"
                          : "text-slate-700"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>{c.displayId}</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600">
                          {c.patient.age}a • {c.patient.gender}
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-500 font-normal truncate">
                        {c.patient.clinicalIndication}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button
              onClick={() => setShowPresetMenu(!showPresetMenu)}
              title="Ajustes de imagen y tinción"
              className="p-1.5 hover:text-slate-900 hover:bg-slate-100 rounded-md transition-colors"
            >
              <Sliders className="w-4 h-4" />
            </button>
            <button
              onClick={() =>
                alert(
                  "Demostración: la configuración del escáner no está conectada. Los ajustes visuales están disponibles en el selector de presets.",
                )
              }
              title="Configuración de escaneo"
              className="p-1.5 hover:text-slate-900 hover:bg-slate-100 rounded-md transition-colors"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>

          {/* Active Case Tab (as shown in reference screenshot) */}
          <div className="ml-1 flex items-center bg-indigo-50/80 border border-indigo-200/90 text-indigo-800 text-xs font-medium px-2.5 py-1 rounded-sm gap-2">
            <span>{activeCase.displayId}</span>
            <button
              onClick={() => setShowCaseDropdown(true)}
              className="text-indigo-400 hover:text-indigo-700 p-0.5 rounded-xs"
              title="Cambiar caso"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Center: Workflow Tabs ("FULL FIELD REVIEW", "SPECIMEN QUALITY", "ANALYSIS AREA", "REVIEW CELLS", "REPORT") */}
        <nav className="flex items-center gap-1">
          {tabs.map((tab) => {
            const isActive = currentTab === tab;
            return (
              <button
                key={tab}
                aria-current={isActive ? "page" : undefined}
                onClick={() => onTabChange(tab)}
                className={`px-3.5 py-1.5 text-xs font-semibold tracking-wider transition-all duration-150 rounded-xs uppercase ${
                  isActive
                    ? "bg-indigo-600 text-white shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                }`}
              >
                {tab}
              </button>
            );
          })}
        </nav>

        {/* Right: Presets, Layout switchers, Patient Info & Standalone HTML */}
        <div className="flex items-center gap-2.5">
          {/* Image Profiles button & presets (Visor exact button group with 1, 2, 3 and Sliders popover) */}
          <div className="relative">
            <div className="flex items-center border border-slate-300 rounded-sm bg-white p-0.5 text-xs shadow-2xs">
              {/* Contrast / Image Profile icon */}
              <span className="p-1 text-slate-500" title="Image Profiles">
                <svg className="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24">
                  <path d="M12,18V6A6,6 0 0,1 18,12A6,6 0 0,1 12,18M20,15.31L23.31,12L20,8.69V4H15.31L12,0.69L8.69,4H4V8.69L0.69,12L4,15.31V20H8.69L12,23.31L15.31,20H20V15.31Z" />
                </svg>
              </span>

              {/* 1, 2, 3 Presets */}
              {[1, 2, 3].map((presetNum) => (
                <button
                  key={presetNum}
                  onClick={() =>
                    onChangeAdjustments({
                      brightness:
                        presetNum === 1 ? 100 : presetNum === 2 ? 115 : 95,
                      contrast:
                        presetNum === 1 ? 100 : presetNum === 2 ? 120 : 110,
                      saturation:
                        presetNum === 1 ? 100 : presetNum === 2 ? 110 : 90,
                      gamma:
                        presetNum === 1 ? 1.0 : presetNum === 2 ? 1.1 : 0.9,
                      preset: presetNum as 1 | 2 | 3,
                    })
                  }
                  className={`w-5 h-5 flex items-center justify-center text-xs font-mono font-medium rounded-xs transition-colors ${
                    imageAdjustments.preset === presetNum
                      ? "bg-[#4D58A4] text-white"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                  title={`Perfil de tinción ${presetNum}`}
                >
                  {presetNum}
                </button>
              ))}

              {/* Sliders popover toggle button */}
              <button
                onClick={() => setShowPresetMenu(!showPresetMenu)}
                className={`p-1 rounded-xs transition-colors ${
                  showPresetMenu || imageAdjustments.preset === "custom"
                    ? "bg-[#4D58A4] text-white"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
                title="Opciones de visualización de la imagen (Brillo, Contraste, Saturación, Gamma)"
              >
                <Sliders className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Exact Visor Image Profiles Popover */}
            {showPresetMenu && (
              <ImageAdjustmentsPopover
                adjustments={imageAdjustments}
                onChange={onChangeAdjustments}
                onReset={() => {
                  onChangeAdjustments({
                    brightness: 100,
                    contrast: 100,
                    saturation: 100,
                    gamma: 1.0,
                    preset: 1,
                  });
                }}
                onClose={() => setShowPresetMenu(false)}
              />
            )}
          </div>

          {/* View mode toggle buttons (Split, Gallery Only, Slide Only) */}
          <div className="flex items-center border border-slate-200 rounded-sm bg-slate-50 p-0.5">
            <button
              onClick={() => onLayoutModeChange("split")}
              className={`p-1 rounded-xs transition-colors ${
                layoutMode === "split"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-500 hover:bg-slate-200"
              }`}
              title="Vista Dividida (Galería + Frotis)"
            >
              <Columns className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onLayoutModeChange("grid")}
              className={`p-1 rounded-xs transition-colors ${
                layoutMode === "grid"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-500 hover:bg-slate-200"
              }`}
              title="Solo Galería de Células"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onLayoutModeChange("slide")}
              className={`p-1 rounded-xs transition-colors ${
                layoutMode === "slide"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-500 hover:bg-slate-200"
              }`}
              title="Solo Vista de Frotis Completo"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Patient Info Chip & Status */}
          <div className="flex items-center gap-2 pl-2 border-l border-slate-200 text-xs">
            <span className="text-slate-400">
              <Edit2 className="w-3 h-3" />
            </span>
            <div className="text-slate-600">
              <span className="font-semibold text-slate-800">INFO:</span>{" "}
              {activeCase.patient.gender}, {activeCase.patient.age}y
            </div>

            {/* Status dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowStatusDropdown(!showStatusDropdown)}
                className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-100 hover:bg-slate-200 transition-colors text-slate-700 font-medium"
              >
                <span className="text-slate-500 font-normal">STATUS:</span>
                <span
                  className={`w-2 h-2 rounded-full ${currentStatusObj.color}`}
                />
                <span>{activeCase.status}</span>
                <ChevronDown className="w-3 h-3 text-slate-400" />
              </button>

              {showStatusDropdown && (
                <div className="absolute right-0 top-full mt-1 w-36 bg-white rounded-md shadow-lg border border-slate-200 py-1 z-50">
                  {statuses.map((s) => (
                    <button
                      key={s.label}
                      onClick={() => {
                        onStatusChange(s.label);
                        setShowStatusDropdown(false);
                      }}
                      className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 flex items-center gap-2 text-slate-700"
                    >
                      <span className={`w-2 h-2 rounded-full ${s.color}`} />
                      <span>{s.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Single-file HTML Autocontenido Button (Exact User Requirement #4) */}
          <button
            onClick={onOpenStandaloneHtml}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-sm hover:bg-indigo-100 transition-colors"
            title="Ver o descargar versión HTML autocontenida de un único archivo"
          >
            <FileCode className="w-3.5 h-3.5" />
            <span className="hidden xl:inline">HTML Autocontenido</span>
          </button>
        </div>
      </div>
    </header>
  );
};
