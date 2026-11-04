import React from "react";
import { CellItem } from "../types/visor";

interface CellMicrographProps {
  cell: CellItem;
  size?: number;
  isSelected?: boolean;
  onClick?: () => void;
  onDoubleClick?: () => void;
  showIdBadge?: boolean;
}

export const CellMicrograph: React.FC<CellMicrographProps> = ({
  cell,
  size = 72,
  isSelected = false,
  onClick,
  onDoubleClick,
  showIdBadge = true,
}) => {
  // Cytological color palettes matching Romanowsky/Wright-Giemsa stain
  const isBlast = cell.category === "Blast";
  const isNeutrophil = cell.category.includes("Neutrophil");
  const isEosinophil = cell.category === "Eosinophil";
  const isBasophil = cell.category === "Basophil";
  const isLymphocyte = cell.category === "Lymphocyte";
  const isMonocyte = cell.category === "Monocyte";
  // Promyelocyte is default
  const isPromyelocyte = cell.category === "Promyelocyte";

  // Seed variation based on cell ID
  const seed = cell.id;
  const nucleusRadius = isBlast
    ? 22
    : isPromyelocyte
      ? 20
      : isLymphocyte
        ? 18
        : 16;
  const cx = 36 + ((seed * 7) % 5) - 2;
  const cy = 36 + ((seed * 11) % 5) - 2;

  return (
    <div
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      title={`${cell.name} #${cell.id} (${(cell.confidence * 100).toFixed(1)}% conf) - Doble click para ampliar`}
      className={`relative cursor-pointer overflow-hidden rounded-xs transition-all duration-150 group select-none aspect-square ${
        isSelected
          ? "ring-3 ring-indigo-500 ring-offset-1 ring-offset-slate-900 shadow-md scale-[1.02] z-10"
          : "hover:brightness-110 hover:ring-1 hover:ring-white/40"
      }`}
      style={{ width: "100%", height: "100%" }}
    >
      {/* Background slide canvas stained field */}
      <svg
        viewBox="0 0 72 72"
        className="w-full h-full block bg-[#d9b6c9]"
        style={{
          filter: cell.abnormal ? "contrast(1.08)" : "none",
        }}
      >
        <defs>
          {/* Chromatin texture filter */}
          <radialGradient id={`nucl-grad-${cell.id}`} cx="40%" cy="35%" r="65%">
            <stop
              offset="0%"
              stopColor={
                isBlast
                  ? "#4e3370"
                  : isPromyelocyte
                    ? "#341f54"
                    : isEosinophil
                      ? "#422858"
                      : isBasophil
                        ? "#1c1236"
                        : "#2a1a45"
              }
            />
            <stop
              offset="70%"
              stopColor={
                isBlast
                  ? "#361e52"
                  : isPromyelocyte
                    ? "#281347"
                    : isEosinophil
                      ? "#321c45"
                      : isBasophil
                        ? "#130c26"
                        : "#1f1035"
              }
            />
            <stop offset="100%" stopColor="#1a0b30" />
          </radialGradient>

          {/* Cytoplasm gradient */}
          <radialGradient id={`cyto-grad-${cell.id}`} cx="50%" cy="50%" r="50%">
            <stop
              offset="0%"
              stopColor={
                isBlast
                  ? "#788bb5"
                  : isPromyelocyte
                    ? "#8590c2"
                    : isEosinophil
                      ? "#dfa1b2"
                      : isBasophil
                        ? "#5b577a"
                        : "#8ca1c9"
              }
            />
            <stop
              offset="85%"
              stopColor={
                isBlast
                  ? "#5c6e99"
                  : isPromyelocyte
                    ? "#6b75a6"
                    : isEosinophil
                      ? "#cf8a9f"
                      : isBasophil
                        ? "#474363"
                        : "#7185ad"
              }
            />
            <stop offset="100%" stopColor="#c79fb4" />
          </radialGradient>
        </defs>

        {/* Surrounding Erythrocytes (RBCs) background field */}
        <g opacity="0.75">
          <circle
            cx="8"
            cy="12"
            r="7.5"
            fill="#e79fb2"
            stroke="#d48096"
            strokeWidth="0.8"
          />
          <circle cx="8" cy="12" r="3.2" fill="#f0bfcb" />
          <circle
            cx="22"
            cy="6"
            r="7.0"
            fill="#e598ac"
            stroke="#cf7b91"
            strokeWidth="0.8"
          />
          <circle cx="22" cy="6" r="3.0" fill="#efb9c6" />
          <circle
            cx="64"
            cy="14"
            r="7.2"
            fill="#e8a2b5"
            stroke="#d58299"
            strokeWidth="0.8"
          />
          <circle cx="64" cy="14" r="3.1" fill="#f2c4d0" />
          <circle
            cx="68"
            cy="38"
            r="6.8"
            fill="#e598ac"
            stroke="#cf7b91"
            strokeWidth="0.8"
          />
          <circle cx="68" cy="38" r="2.9" fill="#efb9c6" />
          <circle
            cx="62"
            cy="62"
            r="7.6"
            fill="#e79fb2"
            stroke="#d48096"
            strokeWidth="0.8"
          />
          <circle cx="62" cy="62" r="3.3" fill="#f0bfcb" />
          <circle
            cx="10"
            cy="64"
            r="7.4"
            fill="#e8a2b5"
            stroke="#d58299"
            strokeWidth="0.8"
          />
          <circle cx="10" cy="64" r="3.2" fill="#f2c4d0" />
          <circle
            cx="6"
            cy="40"
            r="7.0"
            fill="#e598ac"
            stroke="#cf7b91"
            strokeWidth="0.8"
          />
          <circle cx="6" cy="40" r="3.0" fill="#efb9c6" />
        </g>

        {/* Leukocyte Cytoplasm boundary */}
        <ellipse
          cx={cx}
          cy={cy}
          rx={isPromyelocyte ? 29 : isBlast ? 27 : 24}
          ry={isPromyelocyte ? 28 : isBlast ? 26 : 24}
          fill={`url(#cyto-grad-${cell.id})`}
          opacity="0.94"
        />

        {/* Azurophilic Granules for Promyelocytes / Granulocytes */}
        {(isPromyelocyte || isBasophil || isEosinophil) && (
          <g opacity={isBasophil ? "0.95" : isEosinophil ? "0.90" : "0.80"}>
            {[
              [cx - 15, cy - 14, isEosinophil ? "#d84b2c" : "#331649"],
              [cx - 18, cy + 2, isEosinophil ? "#e05938" : "#3d1c57"],
              [cx - 12, cy + 18, isEosinophil ? "#d84b2c" : "#2b1040"],
              [cx + 16, cy - 12, isEosinophil ? "#e05938" : "#3b1854"],
              [cx + 20, cy + 6, isEosinophil ? "#cf4222" : "#452060"],
              [cx + 14, cy + 16, isEosinophil ? "#e05938" : "#2d0e42"],
              [cx - 2, cy - 21, isEosinophil ? "#d84b2c" : "#3f1a5a"],
              [cx + 4, cy + 21, isEosinophil ? "#cf4222" : "#35144e"],
              [cx - 8, cy - 18, isEosinophil ? "#e05938" : "#301147"],
              [cx + 8, cy - 19, isEosinophil ? "#d84b2c" : "#441d61"],
              [cx - 20, cy - 4, isEosinophil ? "#cf4222" : "#381652"],
              [cx + 18, cy - 3, isEosinophil ? "#e05938" : "#2c0f3f"],
              [cx - 10, cy + 20, isEosinophil ? "#d84b2c" : "#411e5c"],
            ].map(([gx, gy, color], idx) => (
              <circle
                key={idx}
                cx={gx as number}
                cy={gy as number}
                r={isBasophil ? 2.6 : isEosinophil ? 2.2 : 1.4}
                fill={color as string}
              />
            ))}
          </g>
        )}

        {/* Nucleus */}
        {isNeutrophil ? (
          // Segmented multi-lobed nucleus
          <g fill={`url(#nucl-grad-${cell.id})`} opacity="0.95">
            <ellipse cx={cx - 10} cy={cy - 6} rx="9" ry="8" />
            <ellipse cx={cx + 8} cy={cy - 7} rx="8" ry="7" />
            <ellipse cx={cx - 1} cy={cy + 8} rx="10" ry="7" />
            {/* Connecting chromatin filaments */}
            <path
              d={`M ${cx - 6} ${cy - 2} Q ${cx - 2} ${cy + 3} ${cx} ${cy + 5}`}
              stroke="#25123d"
              strokeWidth="2.5"
            />
            <path
              d={`M ${cx + 4} ${cy - 2} Q ${cx + 2} ${cy + 3} ${cx} ${cy + 5}`}
              stroke="#25123d"
              strokeWidth="2.5"
            />
          </g>
        ) : (
          // Single large round or indented nucleus
          <g>
            <ellipse
              cx={cx}
              cy={cy}
              rx={nucleusRadius}
              ry={nucleusRadius * (isMonocyte ? 0.8 : 0.92)}
              fill={`url(#nucl-grad-${cell.id})`}
              opacity="0.96"
            />
            {/* Nucleoli visible in Blasts and early Promyelocytes */}
            {(isBlast || (isPromyelocyte && cell.id % 2 === 1)) && (
              <g opacity="0.6">
                <circle cx={cx - 5} cy={cy - 3} r="3.2" fill="#674b8c" />
                <circle cx={cx + 6} cy={cy + 4} r="2.6" fill="#674b8c" />
              </g>
            )}
            {/* Monocyte folded indentation */}
            {isMonocyte && (
              <path
                d={`M ${cx - 12} ${cy} Q ${cx} ${cy + 7} ${cx + 12} ${cy}`}
                fill="none"
                stroke="#1b0e2b"
                strokeWidth="2"
                opacity="0.7"
              />
            )}
          </g>
        )}
      </svg>

      {/* Visor Cell ID Badge (Crisp white numeral overlay on top left) */}
      {showIdBadge && (
        <div className="absolute top-0.5 left-0.5 px-1 py-0.2 text-[9px] font-mono font-medium text-white/90 drop-shadow-[0_1px_2px_rgba(0,0,0,0.85)] tracking-tighter pointer-events-none">
          {cell.id}
        </div>
      )}

      {/* Flag or Abnormal marker */}
      {cell.abnormal && (
        <div className="absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-amber-400 ring-1 ring-black/40 shadow-xs" />
      )}
      {cell.flagged && (
        <div className="absolute bottom-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-rose-500 ring-1 ring-black/40 shadow-xs" />
      )}
    </div>
  );
};
