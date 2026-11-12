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
      color: "text-frotis-success",
      description:
        "Equilibrio espectral cromático correcto entre azul de metileno y eosina. Contraste núcleo-citoplasmático nítido.",
    },
    {
      title: "Homogeneidad de Monocapa (Monolayer Assessment)",
      score: "96.1%",
      status: "Adecuada",
      icon: Layers,
      color: "text-frotis-success",
      description:
        "Área ideal de visualización de eritrocitos sin aglutinación excesiva ni solapamiento celular.",
    },
    {
      title: "Índice de Enfoque Z-Stack (Sharpness Score)",
      score: "99.2%",
      status: "Excelente",
      icon: Focus,
      color: "text-frotis-success",
      description:
        "Resolución micrométrica sub-celular en 100x de inmersión en aceite digital.",
    },
    {
      title: "Preservación de Leucocitos (WBC Integrity)",
      score: "95.8%",
      status: "Buena",
      icon: Sparkles,
      color: "text-frotis-success",
      description:
        "Mínima lisis celular pre-analítica. Morfología de gránulos azurófilos preservada.",
    },
  ];

  return (
    <div className="flex-1 bg-frotis-surface-subtle overflow-y-auto p-6 flex justify-center custom-scrollbar select-none">
      <div className="w-full max-w-4xl bg-frotis-surface shadow-lg border-frotis border-frotis-border rounded-sm p-6 text-frotis-text-heading space-y-6">
        <div>
          <h2 className="text-lg font-bold text-frotis-text-primary tracking-tight">
            EVALUACIÓN AUTOMATIZADA DE CALIDAD DEL ESPECÍMEN
          </h2>
          <p className="text-xs text-frotis-text-secondary">
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
                className="border-frotis border-frotis-border rounded-md p-frotis-component-padding bg-frotis-surface-muted/50 flex flex-col justify-between space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 bg-frotis-selected text-frotis-secondary-hover rounded-sm">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-xs font-bold text-frotis-text-heading">
                      {metric.title}
                    </span>
                  </div>
                  <span
                    className={`text-sm font-mono font-bold ${metric.color}`}
                  >
                    {metric.score}
                  </span>
                </div>
                <p className="text-frotis-label text-frotis-text-control leading-relaxed">
                  {metric.description}
                </p>
                <div className="flex items-center gap-frotis-control-gap text-xs font-medium text-frotis-success-text">
                  <CheckCircle2 className="w-frotis-icon-size h-frotis-icon-size" />
                  <span>Estado: {metric.status}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Scan Area Map Summary */}
        <div className="p-frotis-component-padding border-frotis border-frotis-border rounded-md bg-frotis-surface-muted">
          <h3 className="text-xs font-bold text-frotis-text-body uppercase tracking-wider mb-2">
            Resumen de Escaneo Visor X100HT
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-frotis-component-padding text-xs font-mono">
            <div>
              <span className="text-frotis-text-muted block font-sans">
                Superficie Total:
              </span>
              <span className="font-semibold text-frotis-text-heading">
                {activeCase.scanSizeCm2} cm²
              </span>
            </div>
            <div>
              <span className="text-frotis-text-muted block font-sans">
                Campos HPF Registrados:
              </span>
              <span className="font-semibold text-frotis-text-heading">420 HPFs</span>
            </div>
            <div>
              <span className="text-frotis-text-muted block font-sans">
                Células Detectadas:
              </span>
              <span className="font-semibold text-frotis-text-heading">526 Células</span>
            </div>
            <div>
              <span className="text-frotis-text-muted block font-sans">
                Artefactos / Debris:
              </span>
              <span className="font-semibold text-frotis-success-text">&lt; 0.5%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
