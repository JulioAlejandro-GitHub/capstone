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
    { label: "Reviewing", color: "bg-frotis-warning-marker" },
    { label: "Flagged", color: "bg-frotis-error-accent" },
    { label: "Approved", color: "bg-frotis-success-accent" },
    { label: "Signed-off", color: "bg-frotis-accent" },
  ];

  const currentStatusObj =
    statuses.find((s) => s.label === activeCase.status) || statuses[0];

  return (
    <header className="w-full bg-frotis-surface border-b border-frotis-border shadow-xs frotis-layer-header select-none">
      {/* Top Main Bar */}
      <div className="frotis-header-row px-4 flex items-center justify-between gap-3">
        {/* Left: Visor Logo, Tool Icons, and Active Case Tab */}
        <div className="flex items-center gap-3">
          {/* Visor Logo */}
          <div className="flex items-center gap-2 pr-2 border-r border-frotis-border">
            <div className="w-8 h-8 rounded-md bg-frotis-primary flex items-center justify-center text-frotis-text-inverse shadow-xs">
              <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current">
                <path d="M12 2L4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3zm0 4.5c1.93 0 3.5 1.57 3.5 3.5 0 1.27-.68 2.37-1.7 2.98L15 16h-2v-2h-2v2H9l1.2-3.02C9.18 12.37 8.5 11.27 8.5 10c0-1.93 1.57-3.5 3.5-3.5z" />
              </svg>
            </div>
            <span className="text-xl font-bold tracking-tight text-frotis-text-heading">
              Visor
            </span>
          </div>

          {/* Quick Utility Icons */}
          <div className="flex items-center gap-0.5 text-frotis-text-secondary">
            <button
              onClick={onOpenExport}
              title="Compartir / Exportar reporte o datos"
              className="p-1.5 hover:text-frotis-text-primary hover:bg-frotis-hover rounded-md transition-colors"
            >
              <Share2 className="w-frotis-icon-size h-frotis-icon-size" />
            </button>
            <div className="relative">
              <button
                onClick={() => setShowCaseDropdown(!showCaseDropdown)}
                title="Abrir o cambiar caso clínico"
                className="p-1.5 hover:text-frotis-text-primary hover:bg-frotis-hover rounded-md transition-colors"
              >
                <FolderOpen className="w-frotis-icon-size h-frotis-icon-size" />
              </button>

              {/* Case switcher dropdown */}
              {showCaseDropdown && (
                <div className="absolute top-full left-0 mt-1 w-72 bg-frotis-surface rounded-md shadow-lg border-frotis border-frotis-border py-1 frotis-layer-popover animate-in fade-in slide-in-from-top-1">
                  <div className="px-3 py-1.5 text-xs font-semibold text-frotis-text-muted uppercase tracking-wider border-b border-frotis-surface-subtle">
                    Casos Hematológicos Disponibles
                  </div>
                  {availableCases.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => {
                        onSelectCase(c);
                        setShowCaseDropdown(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-xs hover:bg-frotis-surface-muted flex flex-col gap-0.5 ${
                        c.id === activeCase.id
                          ? "bg-frotis-selected/60 font-semibold text-frotis-secondary-hover"
                          : "text-frotis-text-body"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>{c.displayId}</span>
                        <span className="text-frotis-caption px-1.5 py-0.5 rounded-full bg-frotis-surface-subtle text-frotis-text-control">
                          {c.patient.age}a • {c.patient.gender}
                        </span>
                      </div>
                      <span className="text-frotis-label text-frotis-text-secondary font-normal truncate">
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
              className="p-1.5 hover:text-frotis-text-primary hover:bg-frotis-hover rounded-md transition-colors"
            >
              <Sliders className="w-frotis-icon-size h-frotis-icon-size" />
            </button>
            <button
              onClick={() =>
                alert(
                  "Demostración: la configuración del escáner no está conectada. Los ajustes visuales están disponibles en el selector de presets.",
                )
              }
              title="Configuración de escaneo"
              className="p-1.5 hover:text-frotis-text-primary hover:bg-frotis-hover rounded-md transition-colors"
            >
              <Settings className="w-frotis-icon-size h-frotis-icon-size" />
            </button>
          </div>

          {/* Active Case Tab (as shown in reference screenshot) */}
          <div className="ml-1 flex items-center bg-frotis-selected/80 border-frotis border-frotis-selected-border/90 text-frotis-secondary-strong text-xs font-medium px-2.5 py-1 rounded-sm gap-2">
            <span>{activeCase.displayId}</span>
            <button
              onClick={() => setShowCaseDropdown(true)}
              className="text-frotis-accent-muted hover:text-frotis-secondary-hover p-0.5 rounded-xs"
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
                    ? "bg-frotis-secondary text-frotis-text-inverse shadow-xs"
                    : "text-frotis-text-control hover:text-frotis-text-primary hover:bg-frotis-hover"
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
            <div className="flex items-center border-frotis border-frotis-border-strong rounded-sm bg-frotis-surface p-0.5 text-xs shadow-2xs">
              {/* Contrast / Image Profile icon */}
              <span className="p-1 text-frotis-text-secondary" title="Image Profiles">
                <svg className="w-frotis-icon-size-sm h-frotis-icon-size-sm fill-current" viewBox="0 0 24 24">
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
                  className={`w-frotis-button-size h-frotis-button-size flex items-center justify-center text-xs font-mono font-medium rounded-xs transition-colors ${
                    imageAdjustments.preset === presetNum
                      ? "bg-frotis-primary text-frotis-text-inverse"
                      : "text-frotis-text-control hover:bg-frotis-hover"
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
                    ? "bg-frotis-primary text-frotis-text-inverse"
                    : "text-frotis-text-control hover:bg-frotis-hover"
                }`}
                title="Opciones de visualización de la imagen (Brillo, Contraste, Saturación, Gamma)"
              >
                <Sliders className="w-frotis-icon-size-sm h-frotis-icon-size-sm" />
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
          <div className="flex items-center border-frotis border-frotis-border rounded-sm bg-frotis-surface-muted p-0.5">
            <button
              onClick={() => onLayoutModeChange("split")}
              className={`p-1 rounded-xs transition-colors ${
                layoutMode === "split"
                  ? "bg-frotis-secondary text-frotis-text-inverse"
                  : "text-frotis-text-secondary hover:bg-frotis-border"
              }`}
              title="Vista Dividida (Galería + Frotis)"
            >
              <Columns className="w-frotis-icon-size-sm h-frotis-icon-size-sm" />
            </button>
            <button
              onClick={() => onLayoutModeChange("grid")}
              className={`p-1 rounded-xs transition-colors ${
                layoutMode === "grid"
                  ? "bg-frotis-secondary text-frotis-text-inverse"
                  : "text-frotis-text-secondary hover:bg-frotis-border"
              }`}
              title="Solo Galería de Células"
            >
              <LayoutGrid className="w-frotis-icon-size-sm h-frotis-icon-size-sm" />
            </button>
            <button
              onClick={() => onLayoutModeChange("slide")}
              className={`p-1 rounded-xs transition-colors ${
                layoutMode === "slide"
                  ? "bg-frotis-secondary text-frotis-text-inverse"
                  : "text-frotis-text-secondary hover:bg-frotis-border"
              }`}
              title="Solo Vista de Frotis Completo"
            >
              <Maximize2 className="w-frotis-icon-size-sm h-frotis-icon-size-sm" />
            </button>
          </div>

          {/* Patient Info Chip & Status */}
          <div className="flex items-center gap-2 pl-2 border-l border-frotis-border text-xs">
            <span className="text-frotis-text-muted">
              <Edit2 className="w-3 h-3" />
            </span>
            <div className="text-frotis-text-control">
              <span className="font-semibold text-frotis-text-heading">INFO:</span>{" "}
              {activeCase.patient.gender}, {activeCase.patient.age}y
            </div>

            {/* Status dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowStatusDropdown(!showStatusDropdown)}
                className="flex items-center gap-frotis-control-gap px-2 py-0.5 rounded-full bg-frotis-surface-subtle hover:bg-frotis-border transition-colors text-frotis-text-body font-medium"
              >
                <span className="text-frotis-text-secondary font-normal">STATUS:</span>
                <span
                  className={`w-2 h-2 rounded-full ${currentStatusObj.color}`}
                />
                <span>{activeCase.status}</span>
                <ChevronDown className="w-3 h-3 text-frotis-text-muted" />
              </button>

              {showStatusDropdown && (
                <div className="absolute right-0 top-full mt-1 w-36 bg-frotis-surface rounded-md shadow-lg border-frotis border-frotis-border py-1 frotis-layer-popover">
                  {statuses.map((s) => (
                    <button
                      key={s.label}
                      onClick={() => {
                        onStatusChange(s.label);
                        setShowStatusDropdown(false);
                      }}
                      className="w-full text-left px-3 py-1.5 text-xs hover:bg-frotis-surface-muted flex items-center gap-2 text-frotis-text-body"
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
            className="flex items-center gap-frotis-control-gap px-2.5 py-1 text-xs font-medium text-frotis-secondary-hover bg-frotis-selected border-frotis border-frotis-selected-border rounded-sm hover:bg-frotis-selected-hover transition-colors"
            title="Ver o descargar versión HTML autocontenida de un único archivo"
          >
            <FileCode className="w-frotis-icon-size-sm h-frotis-icon-size-sm" />
            <span className="hidden xl:inline">HTML Autocontenido</span>
          </button>
        </div>
      </div>
    </header>
  );
};
