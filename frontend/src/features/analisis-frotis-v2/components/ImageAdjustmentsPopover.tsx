import React from "react";
import { ImageAdjustments } from "../types/visor";

interface ImageAdjustmentsPopoverProps {
  adjustments: ImageAdjustments;
  onChange: (adj: ImageAdjustments) => void;
  onReset: () => void;
  onClose: () => void;
}

export const ImageAdjustmentsPopover: React.FC<
  ImageAdjustmentsPopoverProps
> = ({ adjustments, onChange, onReset, onClose }) => {
  // Convert brightness/contrast/saturation (50 to 150) to offset percentage (-50% to +50%)
  const getPercentage = (value: number) => {
    const diff = Math.round(value - 100);
    return `${diff >= 0 ? (diff === 0 ? "0%" : `+${diff}%`) : `${diff}%`}`;
  };

  const getGammaPercentage = (gamma: number) => {
    const diff = Math.round((gamma - 1.0) * 100);
    return `${diff >= 0 ? (diff === 0 ? "0%" : `+${diff}%`) : `${diff}%`}`;
  };

  return (
    <div
      className="af2-image-popover absolute top-full right-0 mt-1.5 frotis-layer-popover animate-in fade-in slide-in-from-top-1"
      onClick={(e) => e.stopPropagation()}
    >
      {/* Container matching Visor MuiPaper-root-215 */}
      <div
        className="frotis-adjustments-panel bg-frotis-surface-elevated rounded-md shadow-xl border-frotis border-frotis-border/90 p-frotis-component-padding flex flex-col gap-3.5 select-none text-frotis-text-heading"
      >
        {/* Slider 1: brightness */}
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-normal text-frotis-text-body lowercase w-20 flex-shrink-0">
            brightness
          </p>
          <div className="relative flex-1 flex items-center">
            <input
              type="range"
              min="50"
              max="150"
              step="1"
              value={adjustments.brightness}
              onChange={(e) =>
                onChange({
                  ...adjustments,
                  brightness: Number(e.target.value),
                  preset: "custom",
                })
              }
              className="w-full h-1 bg-frotis-border rounded-lg appearance-none cursor-pointer accent-frotis-primary"
            />
          </div>
          <p className="text-xs font-mono text-center text-frotis-text-control w-10 flex-shrink-0">
            {getPercentage(adjustments.brightness)}
          </p>
        </div>

        {/* Slider 2: contrast */}
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-normal text-frotis-text-body lowercase w-20 flex-shrink-0">
            contrast
          </p>
          <div className="relative flex-1 flex items-center">
            <input
              type="range"
              min="50"
              max="150"
              step="1"
              value={adjustments.contrast}
              onChange={(e) =>
                onChange({
                  ...adjustments,
                  contrast: Number(e.target.value),
                  preset: "custom",
                })
              }
              className="w-full h-1 bg-frotis-border rounded-lg appearance-none cursor-pointer accent-frotis-primary"
            />
          </div>
          <p className="text-xs font-mono text-center text-frotis-text-control w-10 flex-shrink-0">
            {getPercentage(adjustments.contrast)}
          </p>
        </div>

        {/* Slider 3: saturation */}
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-normal text-frotis-text-body lowercase w-20 flex-shrink-0">
            saturation
          </p>
          <div className="relative flex-1 flex items-center">
            <input
              type="range"
              min="50"
              max="150"
              step="1"
              value={adjustments.saturation}
              onChange={(e) =>
                onChange({
                  ...adjustments,
                  saturation: Number(e.target.value),
                  preset: "custom",
                })
              }
              className="w-full h-1 bg-frotis-border rounded-lg appearance-none cursor-pointer accent-frotis-primary"
            />
          </div>
          <p className="text-xs font-mono text-center text-frotis-text-control w-10 flex-shrink-0">
            {getPercentage(adjustments.saturation)}
          </p>
        </div>

        {/* Slider 4: gamma */}
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-normal text-frotis-text-body lowercase w-20 flex-shrink-0">
            gamma
          </p>
          <div className="relative flex-1 flex items-center">
            <input
              type="range"
              min="0.5"
              max="1.5"
              step="0.01"
              value={adjustments.gamma}
              onChange={(e) =>
                onChange({
                  ...adjustments,
                  gamma: Number(e.target.value),
                  preset: "custom",
                })
              }
              className="w-full h-1 bg-frotis-border rounded-lg appearance-none cursor-pointer accent-frotis-primary"
            />
          </div>
          <p className="text-xs font-mono text-center text-frotis-text-control w-10 flex-shrink-0">
            {getGammaPercentage(adjustments.gamma)}
          </p>
        </div>

        {/* RESET Button (Matching the original Visor primary button) */}
        <div className="pt-1 border-t border-frotis-surface-subtle flex justify-end">
          <button
            type="button"
            onClick={onReset}
            className="w-full py-1.5 px-4 bg-frotis-primary hover:bg-frotis-primary-reset-hover text-frotis-text-inverse text-xs font-medium uppercase tracking-wider rounded-xs shadow-xs transition-colors flex items-center justify-center cursor-pointer"
          >
            <span>RESET</span>
          </button>
        </div>
      </div>
    </div>
  );
};
