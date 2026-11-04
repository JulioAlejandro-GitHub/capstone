import React from "react";
import { ClinicalCase } from "../types/visor";
import {
  CheckCircle2,
  AlertCircle,
  Droplets,
  Focus,
  Layers,
  Sparkles,
} from "lucide-react";

interface QualityViewProps {
  activeCase: ClinicalCase;
}

export const QualityView: React.FC<QualityViewProps> = ({ activeCase }) => {
  const qualityMetrics = [
    {
      title: "Calidad de Tinción (Stain Quality Index)",
      score: "98.4%",
      status: "Óptima",
      icon: Droplets,
      color: "text-emerald-600",
      description:
        "Equilibrio espectral cromático correcto entre azul de metileno y eosina. Contraste núcleo-citoplasmático nítido.",
    },
    {
      title: "Homogeneidad de Monocapa (Monolayer Assessment)",
      score: "96.1%",
      status: "Adecuada",
      icon: Layers,
      color: "text-emerald-600",
      description:
        "Área ideal de visualización de eritrocitos sin aglutinación excesiva ni solapamiento celular.",
    },
    {
      title: "Índice de Enfoque Z-Stack (Sharpness Score)",
      score: "99.2%",
      status: "Excelente",
      icon: Focus,
      color: "text-emerald-600",
      description:
        "Resolución micrométrica sub-celular en 100x de inmersión en aceite digital.",
    },
    {
      title: "Preservación de Leucocitos (WBC Integrity)",
      score: "95.8%",
      status: "Buena",
      icon: Sparkles,
      color: "text-emerald-600",
      description:
        "Mínima lisis celular pre-analítica. Morfología de gránulos azurófilos preservada.",
    },
  ];

  return (
    <div className="flex-1 bg-slate-100 overflow-y-auto p-6 flex justify-center custom-scrollbar select-none">
      <div className="w-full max-w-4xl bg-white shadow-lg border border-slate-200 rounded-sm p-6 text-slate-800 space-y-6">
        <div>
          <h2 className="text-lg font-bold text-slate-900 tracking-tight">
            EVALUACIÓN AUTOMATIZADA DE CALIDAD DEL ESPECÍMEN
          </h2>
          <p className="text-xs text-slate-500">
            Control de calidad preanalítico y óptico para frotis de sangre
            periférica y aspirado medular
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {qualityMetrics.map((metric) => {
            const Icon = metric.icon;
            return (
              <div
                key={metric.title}
                className="border border-slate-200 rounded-md p-4 bg-slate-50/50 flex flex-col justify-between space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 bg-indigo-50 text-indigo-700 rounded-sm">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-xs font-bold text-slate-800">
                      {metric.title}
                    </span>
                  </div>
                  <span
                    className={`text-sm font-mono font-bold ${metric.color}`}
                  >
                    {metric.score}
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  {metric.description}
                </p>
                <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-700">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Estado: {metric.status}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Scan Area Map Summary */}
        <div className="p-4 border border-slate-200 rounded-md bg-slate-50">
          <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
            Resumen de Escaneo Visor X100HT
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
            <div>
              <span className="text-slate-400 block font-sans">
                Superficie Total:
              </span>
              <span className="font-semibold text-slate-800">
                {activeCase.scanSizeCm2} cm²
              </span>
            </div>
            <div>
              <span className="text-slate-400 block font-sans">
                Campos HPF Registrados:
              </span>
              <span className="font-semibold text-slate-800">420 HPFs</span>
            </div>
            <div>
              <span className="text-slate-400 block font-sans">
                Células Detectadas:
              </span>
              <span className="font-semibold text-slate-800">526 Células</span>
            </div>
            <div>
              <span className="text-slate-400 block font-sans">
                Artefactos / Debris:
              </span>
              <span className="font-semibold text-emerald-700">&lt; 0.5%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
