import React, { useState, useRef, useEffect, useId } from "react";
import { CellItem, ImageAdjustments, RulerMode } from "../types/visor";
import { calculateScaleBar } from "../utils/hematology";
import { ImageAdjustmentsPopover } from "./ImageAdjustmentsPopover";
import {
  ZoomIn,
  ZoomOut,
  Home,
  Maximize,
  Minimize,
  Grid,
  Square,
  Info,
  Layers,
  Ruler,
  MousePointer,
  RotateCcw,
  Eye,
  EyeOff,
  Filter,
  Sliders,
} from "lucide-react";

interface SlideViewerProps {
  cells: CellItem[];
  selectedCellId: number | null;
  onSelectCell: (cell: CellItem) => void;
  imageAdjustments: ImageAdjustments;
  onChangeAdjustments?: (adj: ImageAdjustments) => void;
  createdDate?: string;
  scanSizeCm2?: number;
}

export const SlideViewer: React.FC<SlideViewerProps> = ({
  cells,
  selectedCellId,
  onSelectCell,
  imageAdjustments,
  onChangeAdjustments,
  createdDate = "04/05/2023 13:47",
  scanSizeCm2 = 2.27,
}) => {
  const gammaId = useId().replace(/:/g, "");
  // Zoom level: 1x (slide overview) to 80x (high power oil immersion)
  const [zoom, setZoom] = useState(25);
  // Pan offsets in pixels
  const [pan, setPan] = useState({ x: -180, y: -80 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Tools state
  const [activeTool, setActiveTool] = useState<"pan" | "ruler" | "grid">("pan");
  const [rulerMode, setRulerMode] = useState<RulerMode>("NONE");
  const [showRulerMenu, setShowRulerMenu] = useState(false);
  const [rulerSizeUm, setRulerSizeUm] = useState<number>(18);
  const [rulerPosition, setRulerPosition] = useState<{ x: number; y: number }>({
    x: 48.2,
    y: 35.4,
  });
  const [isDraggingRuler, setIsDraggingRuler] = useState(false);
  const [rulerDragStart, setRulerDragStart] = useState({ x: 0, y: 0 });
  const [showHpfGrid, setShowHpfGrid] = useState(false);
  const [showCellMarkers, setShowCellMarkers] = useState(true);
  const [showScanInfo, setShowScanInfo] = useState(false);
  const [showImageProfiles, setShowImageProfiles] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [rulerMeasurement, setRulerMeasurement] = useState<string | null>(null);

  // Canvas / container ref
  const containerRef = useRef<HTMLDivElement>(null);

  // When selected cell changes, smoothly center on that cell
  useEffect(() => {
    if (selectedCellId) {
      const cell = cells.find((c) => c.id === selectedCellId);
      if (cell && containerRef.current) {
        const { clientWidth, clientHeight } = containerRef.current;
        // Center pan based on cell percentages
        const targetX = clientWidth / 2 - (cell.x / 100) * 1400 * (zoom / 25);
        const targetY = clientHeight / 2 - (cell.y / 100) * 900 * (zoom / 25);
        setPan({ x: targetX, y: targetY });
        setRulerPosition({ x: cell.x, y: cell.y });
        if (cell.diameterUm) {
          setRulerSizeUm(Math.round(cell.diameterUm));
        }
      }
    }
  }, [selectedCellId]);

  const recenterRuler = () => {
    if (selectedCellId) {
      const cell = cells.find((c) => c.id === selectedCellId);
      if (cell) {
        setRulerPosition({ x: cell.x, y: cell.y });
        return;
      }
    }
    setRulerPosition({ x: 50, y: 50 });
  };

  // Handle Mouse Drag / Pan
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDraggingRuler) {
      const dx = ((e.clientX - rulerDragStart.x) / (1400 * (zoom / 25))) * 100;
      const dy = ((e.clientY - rulerDragStart.y) / (900 * (zoom / 25))) * 100;
      setRulerPosition((prev) => ({
        x: Math.max(5, Math.min(95, prev.x + dx)),
        y: Math.max(5, Math.min(95, prev.y + dy)),
      }));
      setRulerDragStart({ x: e.clientX, y: e.clientY });
      return;
    }
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setIsDraggingRuler(false);
  };

  // Handle Wheel Zoom
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    setZoom((prev) => Math.min(100, Math.max(1.5, prev * zoomFactor)));
  };

  // Zoom controls
  const zoomIn = () => setZoom((prev) => Math.min(100, prev * 1.3));
  const zoomOut = () => setZoom((prev) => Math.max(1.5, prev / 1.3));
  const resetView = () => {
    setZoom(25);
    setPan({ x: -180, y: -80 });
  };

  const scaleBar = calculateScaleBar(zoom);

  // Minimap indicator bounds calculation
  const minimapWidth = 120;
  const minimapHeight = 160;
  const viewportWidth = Math.max(
    20,
    Math.min(minimapWidth, minimapWidth / (zoom / 10)),
  );
  const viewportHeight = Math.max(
    15,
    Math.min(minimapHeight, minimapHeight / (zoom / 10)),
  );
  const viewportLeft = Math.max(
    0,
    Math.min(minimapWidth - viewportWidth, -pan.x / 25),
  );
  const viewportTop = Math.max(
    0,
    Math.min(minimapHeight - viewportHeight, -pan.y / 25),
  );

  return (
    <div
      ref={containerRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onWheel={handleWheel}
      className={`relative flex-1 h-full bg-[#e8d5df] overflow-hidden select-none cursor-${
        activeTool === "ruler" ? "crosshair" : isDragging ? "grabbing" : "grab"
      }`}
    >
      <svg width="0" height="0" aria-hidden="true">
        <defs>
          <filter id={gammaId}>
            <feComponentTransfer>
              {["R", "G", "B"].map((channel) => {
                const Func = `feFunc${channel}` as "feFuncR";
                return (
                  <Func
                    key={channel}
                    type="gamma"
                    amplitude={1}
                    exponent={1 / imageAdjustments.gamma}
                    offset={0}
                  />
                );
              })}
            </feComponentTransfer>
          </filter>
        </defs>
      </svg>
      {/* Microscopic Slide Canvas rendering Romanowsky-Giemsa blood smear */}
      <div
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom / 25})`,
          transformOrigin: "0 0",
          transition: isDragging ? "none" : "transform 120ms ease-out",
          filter: `url(#${gammaId}) brightness(${imageAdjustments.brightness}%) contrast(${imageAdjustments.contrast}%) saturate(${imageAdjustments.saturation}%)`,
        }}
        className="absolute left-0 top-0 w-[1400px] h-[900px] pointer-events-auto"
      >
        {/* Slide background smear image with cells */}
        <div className="relative w-full h-full bg-[#efd7e3] overflow-hidden shadow-2xl">
          {/* Base histological texture with thousands of red blood cells (erythrocytes) */}
          <svg className="w-full h-full absolute inset-0 opacity-90 pointer-events-none">
            <defs>
              <pattern
                id="rbc-field"
                width="40"
                height="40"
                patternUnits="userSpaceOnUse"
              >
                {/* Erythrocytes with biconcave pale centers */}
                <circle
                  cx="10"
                  cy="10"
                  r="7"
                  fill="#df97ab"
                  stroke="#cc778e"
                  strokeWidth="0.8"
                />
                <circle cx="10" cy="10" r="3" fill="#ecd0d8" />
                <circle
                  cx="30"
                  cy="12"
                  r="7.2"
                  fill="#e29db0"
                  stroke="#cf7e94"
                  strokeWidth="0.8"
                />
                <circle cx="30" cy="12" r="3.2" fill="#eed3db" />
                <circle
                  cx="12"
                  cy="30"
                  r="6.8"
                  fill="#dd92a7"
                  stroke="#cb728a"
                  strokeWidth="0.8"
                />
                <circle cx="12" cy="30" r="2.9" fill="#eaccd5" />
                <circle
                  cx="32"
                  cy="32"
                  r="7"
                  fill="#e09aa9"
                  stroke="#ce7b90"
                  strokeWidth="0.8"
                />
                <circle cx="32" cy="32" r="3" fill="#ebd2dc" />
                <circle
                  cx="21"
                  cy="21"
                  r="6.9"
                  fill="#e19bb0"
                  stroke="#cd7a91"
                  strokeWidth="0.8"
                />
                <circle cx="21" cy="21" r="3" fill="#edd5dd" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#rbc-field)" />
          </svg>

          {/* Render Detected Leukocytes / Promyelocytes scattered across slide */}
          {cells.map((cell) => {
            const isSelected = cell.id === selectedCellId;
            return (
              <div
                key={cell.id}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectCell(cell);
                }}
                style={{
                  left: `${cell.x}%`,
                  top: `${cell.y}%`,
                  transform: "translate(-50%, -50%)",
                }}
                className="absolute cursor-pointer group"
              >
                {/* Visual cell body on the slide */}
                <div className="relative w-12 h-12 flex items-center justify-center">
                  {/* Surrounding cytoplasm */}
                  <div className="w-11 h-11 rounded-full bg-[#707ea6]/90 border border-[#526087] shadow-sm flex items-center justify-center">
                    {/* Dark purple nucleus */}
                    <div className="w-7 h-7 rounded-full bg-[#2c1448] shadow-inner" />
                  </div>

                  {/* Cell marker overlay ring (Toggleable) */}
                  {showCellMarkers && (
                    <div
                      className={`absolute -inset-1 rounded-full pointer-events-none transition-all duration-200 ${
                        isSelected
                          ? "border-2 border-indigo-600 ring-4 ring-indigo-400/50 scale-125 animate-pulse"
                          : "border border-dashed border-indigo-500/70 opacity-60 group-hover:opacity-100 group-hover:scale-110"
                      }`}
                    />
                  )}

                  {/* Tooltip on hover */}
                  <div className="absolute -top-7 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 bg-slate-900/90 text-white text-[10px] px-1.5 py-0.5 rounded-xs whitespace-nowrap pointer-events-none shadow-md z-30 font-mono">
                    {cell.name} #{cell.id}
                  </div>
                </div>
              </div>
            );
          })}

          {/* High Power Field (HPF) Grid Overlay */}
          {showHpfGrid && (
            <div className="absolute inset-0 pointer-events-none grid grid-cols-12 grid-rows-8 divide-x divide-y divide-indigo-500/30">
              {Array.from({ length: 96 }).map((_, idx) => (
                <div key={idx} className="relative">
                  <span className="absolute bottom-1 right-1 text-[9px] font-mono text-indigo-700/50">
                    HPF-{idx + 1}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Interactive On-Screen Ruler Caliper Reticle */}
          {rulerMode !== "NONE" && (
            <div
              style={{
                left: `${rulerPosition.x}%`,
                top: `${rulerPosition.y}%`,
                transform: "translate(-50%, -50%)",
              }}
              onMouseDown={(e) => {
                e.stopPropagation();
                setIsDraggingRuler(true);
                setRulerDragStart({ x: e.clientX, y: e.clientY });
              }}
              className="absolute cursor-move z-30 select-none group"
              title="Arrastra para medir cualquier célula en el frotis"
            >
              {rulerMode === "CIRCLE" && (
                <div className="relative flex items-center justify-center">
                  <div
                    style={{
                      width: `${rulerSizeUm * 2.8}px`,
                      height: `${rulerSizeUm * 2.8}px`,
                    }}
                    className="rounded-full border-2 border-indigo-600 bg-indigo-500/15 shadow-sm flex items-center justify-center relative hover:ring-2 hover:ring-indigo-400"
                  >
                    <div className="w-1.5 h-1.5 rounded-full bg-indigo-700" />
                    <div className="absolute inset-x-0 top-1/2 h-px bg-indigo-600/40" />
                    <div className="absolute inset-y-0 left-1/2 w-px bg-indigo-600/40" />
                  </div>
                  <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-slate-900/90 text-white text-[10px] font-mono font-semibold px-2 py-0.5 rounded-sm shadow-md whitespace-nowrap pointer-events-none">
                    ⌀ {rulerSizeUm} µm
                  </div>
                </div>
              )}

              {rulerMode === "CROSS" && (
                <div className="relative flex items-center justify-center">
                  <div
                    style={{
                      width: `${rulerSizeUm * 3.4}px`,
                      height: `${rulerSizeUm * 3.4}px`,
                    }}
                    className="relative flex items-center justify-center"
                  >
                    <div className="absolute inset-x-0 top-1/2 h-0.5 bg-indigo-600 shadow-sm" />
                    <div className="absolute inset-y-0 left-1/2 w-0.5 bg-indigo-600 shadow-sm" />
                    <div className="w-2.5 h-2.5 rounded-full border border-indigo-600 bg-white/40" />
                  </div>
                  <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-slate-900/90 text-white text-[10px] font-mono font-semibold px-2 py-0.5 rounded-sm shadow-md whitespace-nowrap pointer-events-none">
                    CROSS: {rulerSizeUm} µm
                  </div>
                </div>
              )}

              {rulerMode === "LINE" && (
                <div className="relative flex items-center justify-center">
                  <div
                    style={{ width: `${rulerSizeUm * 3.2}px` }}
                    className="h-1 bg-indigo-600 border-x-4 border-indigo-800 relative shadow-sm"
                  />
                  <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-slate-900/90 text-white text-[10px] font-mono font-semibold px-2 py-0.5 rounded-sm shadow-md whitespace-nowrap pointer-events-none">
                    {rulerSizeUm} µm
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Top Floating Visor Toolbar (Iconic white pill overlay from Visor) */}
      <div className="absolute top-3 left-4 z-30 flex items-center gap-1.5 bg-white/95 backdrop-blur-sm border border-slate-200/90 shadow-md rounded-sm px-1.5 py-1">
        {/* Ruler tool with exact Visor Dropdown menu */}
        <span title="Ruler" className="relative">
          <div className="MuiBox-root-9 jss1036 sc-iwyWTf kqlMG">
            <button
              onClick={() => setShowRulerMenu(!showRulerMenu)}
              className={`p-1.5 rounded-xs flex items-center gap-1 text-xs transition-colors cursor-pointer ${
                rulerMode !== "NONE"
                  ? "bg-[#4D58A4] text-white"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
              tabIndex={0}
              type="button"
              data-sl-test="sv-toolbar-rulerButton"
            >
              <div className="flex items-center gap-1">
                <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                  <path d="M1.39,18.36L3.16,16.6L4.58,18L5.64,16.95L4.22,15.54L5.64,14.12L8.11,16.6L9.17,15.54L6.7,13.06L8.11,11.65L9.53,13.06L10.59,12L9.17,10.59L10.59,9.17L13.06,11.65L14.12,10.59L11.65,8.11L13.06,6.7L14.47,8.11L15.54,7.05L14.12,5.64L15.54,4.22L18,6.7L19.07,5.64L16.6,3.16L18.36,1.39L22.61,5.64L5.64,22.61L1.39,18.36Z" />
                </svg>
                <span className="text-[11px] font-medium hidden sm:inline">
                  {rulerMode !== "NONE" ? rulerMode : "Regla"}
                </span>
                <svg className="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24">
                  <path d="M7,10L12,15L17,10H7Z" />
                </svg>
              </div>
            </button>
          </div>

          {/* Exact Visor Popover Menu */}
          {showRulerMenu && (
            <div
              className="MuiPaper-root-73 MuiMenu-paper-61 MuiPopover-paper-64 MuiPaper-elevation8-84 MuiPaper-rounded-74 absolute top-full left-0 mt-1 z-50 bg-white rounded-sm shadow-xl border border-slate-200 py-1 w-32 animate-in fade-in"
              tabIndex={-1}
              onClick={(e) => e.stopPropagation()}
            >
              <ul
                className="MuiList-root-460 MuiMenu-list-62 MuiList-padding-461 text-xs text-slate-800 font-medium"
                role="menu"
              >
                {(["NONE", "LINE", "CROSS", "CIRCLE"] as RulerMode[]).map(
                  (mode) => (
                    <li
                      key={mode}
                      onClick={() => {
                        setRulerMode(mode);
                        setShowRulerMenu(false);
                      }}
                      className={`px-3 py-1.5 hover:bg-slate-100 cursor-pointer flex items-center justify-between transition-colors ${
                        rulerMode === mode
                          ? "bg-indigo-50 text-[#4D58A4] font-bold"
                          : ""
                      }`}
                      data-sl-test={`option:${mode.toLowerCase()}`}
                      role="menuitem"
                    >
                      <div className="MuiBox-root-9">{mode}</div>
                      {rulerMode === mode && (
                        <span className="text-[#4D58A4] text-[10px]">●</span>
                      )}
                    </li>
                  ),
                )}
              </ul>
            </div>
          )}
        </span>

        {/* HPF Grid toggle */}
        <button
          onClick={() => setShowHpfGrid(!showHpfGrid)}
          className={`p-1.5 rounded-xs flex items-center gap-1 text-xs transition-colors ${
            showHpfGrid
              ? "bg-indigo-600 text-white"
              : "text-slate-700 hover:bg-slate-100"
          }`}
          title="Rejilla HPF (Campo de Gran Aumento)"
        >
          <Grid className="w-4 h-4" />
          <span className="text-[11px] font-medium hidden sm:inline">
            HPF Grid
          </span>
        </button>

        {/* Magnification Preset Selector (10x, 20x, 40x, 100x) */}
        <div className="flex items-center border-l border-r border-slate-200 px-1 mx-0.5 gap-0.5">
          {[10, 20, 40, 100].map((mag) => (
            <button
              key={mag}
              onClick={() => setZoom(mag)}
              className={`px-1.5 py-0.5 text-xs font-mono font-medium rounded-xs transition-colors ${
                Math.round(zoom) === mag
                  ? "bg-indigo-600 text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {mag}x
            </button>
          ))}
        </div>

        {/* Cell Markers Toggle */}
        <button
          onClick={() => setShowCellMarkers(!showCellMarkers)}
          className={`p-1.5 rounded-xs text-slate-700 hover:bg-slate-100 transition-colors ${
            showCellMarkers ? "text-indigo-600" : "text-slate-400"
          }`}
          title={
            showCellMarkers
              ? "Ocultar marcadores celulares"
              : "Mostrar marcadores celulares"
          }
        >
          {showCellMarkers ? (
            <Eye className="w-4 h-4" />
          ) : (
            <EyeOff className="w-4 h-4" />
          )}
        </button>

        {/* Image Profiles button (Visor floating toolbar) */}
        {onChangeAdjustments && (
          <div className="relative">
            <button
              onClick={() => setShowImageProfiles(!showImageProfiles)}
              className={`p-1.5 rounded-xs text-slate-700 hover:bg-slate-100 transition-colors ${
                showImageProfiles ? "bg-[#4D58A4] text-white" : "text-slate-700"
              }`}
              title="Ajustes de imagen (Brillo, Contraste, Saturación, Gamma)"
            >
              <Sliders className="w-4 h-4" />
            </button>

            {showImageProfiles && (
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
                onClose={() => setShowImageProfiles(false)}
              />
            )}
          </div>
        )}

        {/* Zoom controls */}
        <div className="flex items-center gap-0.5 pl-1 border-l border-slate-200">
          <button
            onClick={zoomOut}
            className="p-1.5 text-slate-700 hover:bg-slate-100 rounded-xs"
            title="Alejar (-)"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={zoomIn}
            className="p-1.5 text-slate-700 hover:bg-slate-100 rounded-xs"
            title="Acercar (+)"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={resetView}
            className="p-1.5 text-slate-700 hover:bg-slate-100 rounded-xs"
            title="Restablecer posición inicial"
          >
            <Home className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Visor Ruler Overlay Bar (sc-bqyKOL kbpeIU) with Size Slider & Recenter Button */}
      {rulerMode !== "NONE" && (
        <div className="sc-bqyKOL kbpeIU absolute top-14 left-4 z-30 flex items-center gap-3 bg-white/95 backdrop-blur-sm border border-slate-200/90 shadow-md rounded-sm px-3 py-2 select-none w-72 sm:w-80 animate-in fade-in slide-in-from-top-1">
          {/* Ruler Icon with right margin */}
          <svg
            className="MuiSvgIcon-root-397 w-5 h-5 fill-slate-700 flex-shrink-0"
            focusable="false"
            viewBox="0 0 24 24"
            aria-hidden="true"
            style={{ marginRight: "1rem" }}
          >
            <path d="M1.39,18.36L3.16,16.6L4.58,18L5.64,16.95L4.22,15.54L5.64,14.12L8.11,16.6L9.17,15.54L6.7,13.06L8.11,11.65L9.53,13.06L10.59,12L9.17,10.59L10.59,9.17L13.06,11.65L14.12,10.59L11.65,8.11L13.06,6.7L14.47,8.11L15.54,7.05L14.12,5.64L15.54,4.22L18,6.7L19.07,5.64L16.6,3.16L18.36,1.39L22.61,5.64L5.64,22.61L1.39,18.36Z" />
          </svg>

          {/* Stepped Size Slider (5µm, 10µm, 15µm, 20µm) */}
          <div className="flex-1 flex flex-col justify-center">
            <div className="relative flex items-center">
              <input
                type="range"
                min="5"
                max="20"
                step="1"
                value={rulerSizeUm}
                onChange={(e) => setRulerSizeUm(Number(e.target.value))}
                className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#4D58A4]"
                data-sl-test="sv-rulerOverlay-sizeSlider"
              />
            </div>
            {/* Marks 5µm, 10µm, 15µm, 20µm */}
            <div className="flex justify-between text-[10px] font-mono text-slate-500 mt-1">
              <span
                className={rulerSizeUm <= 7 ? "text-[#4D58A4] font-bold" : ""}
              >
                5μm
              </span>
              <span
                className={
                  rulerSizeUm >= 8 && rulerSizeUm <= 12
                    ? "text-[#4D58A4] font-bold"
                    : ""
                }
              >
                10μm
              </span>
              <span
                className={
                  rulerSizeUm >= 13 && rulerSizeUm <= 17
                    ? "text-[#4D58A4] font-bold"
                    : ""
                }
              >
                15μm
              </span>
              <span
                className={rulerSizeUm >= 18 ? "text-[#4D58A4] font-bold" : ""}
              >
                20μm
              </span>
            </div>
          </div>

          {/* Recenter ruler button */}
          <span title="Recenter ruler">
            <button
              onClick={recenterRuler}
              className="MuiButtonBase-root-448 MuiIconButton-root-440 p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-colors cursor-pointer"
              tabIndex={0}
              type="button"
              data-sl-test="sv-rulerOverlay-recenterRulerButton"
            >
              <svg
                className="MuiSvgIcon-root-397 w-5 h-5 fill-current"
                focusable="false"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path d="M12 8C8.44 8 6.65 12.31 9.17 14.83C11.69 17.35 16 15.56 16 12C16 9.79 14.21 8 12 8M5 15H3V19C3 20.1 3.9 21 5 21H9V19H5M5 5H9V3H5C3.9 3 3 3.9 3 5V9H5M19 3H15V5H19V9H21V5C21 3.9 20.1 3 19 3M19 19H15V21H19C20.1 21 21 20.1 21 19V15H19" />
              </svg>
            </button>
          </span>
        </div>
      )}

      {/* Measurement readout badge if ruler used */}
      {rulerMeasurement && (
        <div className="absolute top-16 left-4 bg-slate-900/90 text-white px-3 py-1.5 rounded-md shadow-lg text-xs font-mono flex items-center gap-2 z-20">
          <Ruler className="w-3.5 h-3.5 text-indigo-400" />
          <span>
            Distancia medida: <strong>{rulerMeasurement}</strong>
          </span>
          <button
            onClick={() => setRulerMeasurement(null)}
            className="text-slate-400 hover:text-white text-xs ml-1"
          >
            ✕
          </button>
        </div>
      )}

      {/* Top Right Minimap (Navigator) with Live Glass Slide Overview */}
      <div className="absolute top-3 right-4 z-10 bg-white/95 backdrop-blur-sm border border-slate-300 rounded-sm shadow-md p-1.5 select-none hidden md:block">
        <div className="text-[10px] font-semibold text-slate-500 mb-1 flex items-center justify-between">
          <span>PORTAOBJETOS (SLIDE)</span>
          <span className="font-mono text-indigo-600">{Math.round(zoom)}x</span>
        </div>
        <div
          style={{ width: `${minimapWidth}px`, height: `${minimapHeight}px` }}
          className="relative bg-[#d8b8ca] border border-slate-300 rounded-xs overflow-hidden cursor-pointer"
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const clickY = e.clientY - rect.top;
            setPan({
              x: -(clickX / minimapWidth) * 1400 * (zoom / 25) + 200,
              y: -(clickY / minimapHeight) * 900 * (zoom / 25) + 150,
            });
          }}
        >
          {/* Slide label boundary */}
          <div className="absolute top-0 left-0 right-0 h-4 bg-white/70 border-b border-slate-300 flex items-center px-1 text-[8px] font-mono text-slate-600">
            SCP-16532
          </div>
          {/* Smear area representation */}
          <div className="absolute inset-x-2 top-6 bottom-4 rounded-full bg-[#af5d85]/40 blur-[1px]" />

          {/* Draggable Viewport Indicator (Matching Visor indigo rectangle) */}
          <div
            style={{
              left: `${viewportLeft}px`,
              top: `${viewportTop}px`,
              width: `${viewportWidth}px`,
              height: `${viewportHeight}px`,
            }}
            className="absolute border-2 border-indigo-600 rounded-xs bg-indigo-500/20 shadow-xs pointer-events-none"
          />
        </div>
      </div>

      {/* Bottom Left Scale Bar (Realistic µm display) */}
      <div className="absolute bottom-3 left-4 z-20 bg-white/90 backdrop-blur-sm border border-slate-200 px-3 py-1.5 rounded-sm shadow-sm flex flex-col items-center select-none">
        <div
          style={{ width: `${scaleBar.widthPx}px` }}
          className="h-1 bg-slate-900 border-x-2 border-slate-900 relative mb-1"
        />
        <span className="text-[11px] font-mono font-semibold text-slate-800">
          {scaleBar.label}
        </span>
      </div>

      {/* Bottom Right Scan Info Toggle Button & Drawer */}
      <div className="absolute bottom-3 right-4 z-20 flex flex-col items-end gap-2">
        {showScanInfo && (
          <div className="w-64 bg-slate-900/95 text-white border border-slate-700 rounded-md p-3 shadow-xl text-xs space-y-2 animate-in fade-in slide-in-from-bottom-2">
            <div className="flex items-center justify-between border-b border-slate-700 pb-1.5">
              <span className="font-semibold text-indigo-300">
                Scan Metadata
              </span>
              <button
                onClick={() => setShowScanInfo(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Created:</span>
              <span className="font-mono">{createdDate}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Scan Size:</span>
              <span className="font-mono">{scanSizeCm2} cm²</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Resolution:</span>
              <span className="font-mono">100x Oil Immersion</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Stain Profile:</span>
              <span className="font-mono">Wright-Giemsa</span>
            </div>
            <div className="pt-1 border-t border-slate-800 text-[10px] text-slate-400">
              Visor Full-Field 100x Digital Morphology Scanner
            </div>
          </div>
        )}

        <button
          onClick={() => setShowScanInfo(!showScanInfo)}
          className={`p-2 rounded-full shadow-md border transition-colors ${
            showScanInfo
              ? "bg-indigo-600 text-white border-indigo-700"
              : "bg-white text-slate-700 border-slate-200 hover:bg-slate-100"
          }`}
          title="Ver metadatos del escaneo (Scan Info)"
        >
          <Info className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
