import React, { useState } from "react";
import { ClinicalCase } from "../types/visor";
import {
  FileText,
  Printer,
  Download,
  CheckCircle2,
  AlertTriangle,
  UserCheck,
  ShieldCheck,
} from "lucide-react";

interface ReportViewProps {
  activeCase: ClinicalCase;
  onSignReport: () => void;
}

export const ReportView: React.FC<ReportViewProps> = ({
  activeCase,
  onSignReport,
}) => {
  const [pathologistName, setPathologistName] = useState(
    "Dra. Claudia Benítez - Hematopatóloga",
  );
  const [diagnosticImpression, setDiagnosticImpression] = useState(
    "Frotis y médula ósea con marcado incremento de promyelocitos hipergranulares con núcleos hendidos (68.6%) y blastos mieloides (22.0%), compatible con Leucemia Promielocítica Aguda (LPA / M3 según clasificación FAB). Se recomienda confirmación urgente por RT-PCR o FISH para t(15;17)(q24;q21) / PML-RARA e inicio protocolizado con ATRA.",
  );
  const isSigned = activeCase.status === "Signed-off";

  const handleSign = () => {
    onSignReport();
    alert(
      "Firma simulada aplicada solo en esta sesión. No se ha firmado ni guardado un informe clínico.",
    );
  };

  return (
    <div className="flex-1 bg-frotis-surface-subtle overflow-y-auto p-6 flex justify-center custom-scrollbar">
      <div className="w-full max-w-4xl bg-frotis-surface shadow-lg border-frotis border-frotis-border rounded-sm p-8 text-frotis-text-heading space-y-6">
        {/* Report Top Header */}
        <div className="flex items-center justify-between border-b-2 border-frotis-primary pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-md bg-frotis-primary flex items-center justify-center text-frotis-text-inverse">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-frotis-text-primary">
                INFORME DE MORFOLOGÍA HEMATOLÓGICA DIGITAL
              </h1>
              <p className="text-xs text-frotis-text-secondary font-mono">
                Sistema Visor Full-Field Digital Morphology Analyzer
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => window.print()}
              className="px-3 py-1.5 border-frotis border-frotis-border-strong hover:bg-frotis-surface-muted rounded-sm text-xs font-medium text-frotis-text-body flex items-center gap-frotis-control-gap transition-colors"
            >
              <Printer className="w-frotis-icon-size h-frotis-icon-size" /> Imprimir
            </button>
            <button
              onClick={() =>
                alert(
                  "Demostración: no se genera un PDF clínico. Use Imprimir para guardar una copia local.",
                )
              }
              className="px-3 py-1.5 bg-frotis-primary hover:bg-frotis-primary-hover text-frotis-text-inverse rounded-sm text-xs font-medium flex items-center gap-frotis-control-gap transition-colors shadow-xs"
            >
              <Download className="w-frotis-icon-size h-frotis-icon-size" /> Exportar PDF
            </button>
          </div>
        </div>

        {/* Patient and Specimen Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-frotis-component-padding p-frotis-component-padding bg-frotis-surface-muted border-frotis border-frotis-border rounded-sm text-xs">
          <div>
            <span className="text-frotis-text-muted block font-medium">Paciente</span>
            <span className="font-semibold text-frotis-text-primary text-sm">
              {activeCase.patient.name}
            </span>
          </div>
          <div>
            <span className="text-frotis-text-muted block font-medium">
              Edad / Sexo
            </span>
            <span className="font-semibold text-frotis-text-heading">
              {activeCase.patient.age} años / {activeCase.patient.gender}
            </span>
          </div>
          <div>
            <span className="text-frotis-text-muted block font-medium">
              Nº Caso / MRN
            </span>
            <span className="font-mono font-semibold text-frotis-secondary-hover">
              {activeCase.displayId}
            </span>
          </div>
          <div>
            <span className="text-frotis-text-muted block font-medium">
              Fecha Colección
            </span>
            <span className="font-mono text-frotis-text-body">
              {activeCase.patient.collectionDate}
            </span>
          </div>
          <div className="col-span-2">
            <span className="text-frotis-text-muted block font-medium">
              Tipo de Muestra
            </span>
            <span className="text-frotis-text-body">
              {activeCase.patient.sampleType}
            </span>
          </div>
          <div className="col-span-2">
            <span className="text-frotis-text-muted block font-medium">
              Médico Solicitante
            </span>
            <span className="text-frotis-text-body">
              {activeCase.patient.orderingPhysician}
            </span>
          </div>
        </div>

        {/* Differential Leukocyte Count Breakdown */}
        <div>
          <h2 className="text-sm font-bold text-frotis-text-heading uppercase tracking-wider mb-2 flex items-center justify-between">
            <span>Fórmula Leucocitaria Digital (500 Células Nucleadas)</span>
            <span className="text-xs text-frotis-text-secondary font-normal">
              Área escaneada: {activeCase.scanSizeCm2} cm²
            </span>
          </h2>
          <div className="border-frotis border-frotis-border rounded-sm overflow-hidden text-xs">
            <table className="w-full text-left">
              <thead className="bg-frotis-surface-subtle text-frotis-text-control border-b border-frotis-border font-semibold">
                <tr>
                  <th className="py-2 px-3">Célula / Linaje</th>
                  <th className="py-2 px-3 text-right">Recuento</th>
                  <th className="py-2 px-3 text-right">Porcentaje (%)</th>
                  <th className="py-2 px-3 text-right">Rango Referencia</th>
                  <th className="py-2 px-3 text-center">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-frotis-surface-subtle font-mono">
                {activeCase.categories
                  .filter((c) => c.count > 0)
                  .map((cat) => {
                    const isHigh =
                      cat.name === "Promyelocyte" || cat.name === "Blast";
                    return (
                      <tr
                        key={cat.name}
                        className={isHigh ? "bg-frotis-warning-surface/70 font-semibold" : ""}
                      >
                        <td className="py-1.5 px-3 font-sans text-frotis-text-heading">
                          {cat.name}
                        </td>
                        <td className="py-1.5 px-3 text-right">{cat.count}</td>
                        <td className="py-1.5 px-3 text-right text-frotis-secondary-hover font-bold">
                          {cat.percentage}%
                        </td>
                        <td className="py-1.5 px-3 text-right text-frotis-text-secondary">
                          {cat.referenceRange || "--"}
                        </td>
                        <td className="py-1.5 px-3 text-center">
                          {isHigh ? (
                            <span className="px-2 py-0.5 rounded-full text-frotis-caption bg-frotis-error-subtle text-frotis-error-text font-sans font-semibold">
                              ANÓMALO ELEVADO
                            </span>
                          ) : (
                            <span className="text-frotis-success text-frotis-caption font-sans">
                              Normal
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Diagnostic Impression Field */}
        <div className="space-y-2">
          <label className="block text-sm font-bold text-frotis-text-heading uppercase tracking-wider">
            Impresión Diagnóstica y Comentarios del Hematopatólogo
          </label>
          <textarea
            rows={4}
            value={diagnosticImpression}
            onChange={(e) => setDiagnosticImpression(e.target.value)}
            disabled={isSigned}
            className="w-full p-3 border-frotis border-frotis-border-strong rounded-sm text-xs leading-relaxed text-frotis-text-heading focus:outline-none focus:ring-1 focus:ring-frotis-accent focus:border-frotis-accent bg-frotis-surface disabled:bg-frotis-disabled"
          />
        </div>

        {/* Digital Signature & Sign-off Section */}
        <div className="pt-4 border-t border-frotis-border flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center ${
                isSigned
                  ? "bg-frotis-success-subtle text-frotis-success-text"
                  : "bg-frotis-warning-subtle text-frotis-warning-text"
              }`}
            >
              {isSigned ? (
                <ShieldCheck className="w-6 h-6" />
              ) : (
                <AlertTriangle className="w-5 h-5" />
              )}
            </div>
            <div>
              <div className="text-xs font-semibold text-frotis-text-primary">
                {isSigned
                  ? "Informe Firmado Digitalmente"
                  : "Pendiente de Validación y Firma"}
              </div>
              <div className="text-frotis-label text-frotis-text-secondary">
                Validador: {pathologistName}
              </div>
            </div>
          </div>

          {!isSigned ? (
            <button
              onClick={handleSign}
              className="px-5 py-2 bg-frotis-success hover:bg-frotis-success-text text-frotis-text-inverse font-medium text-xs rounded-sm shadow-sm flex items-center gap-2 transition-colors cursor-pointer"
            >
              <UserCheck className="w-frotis-icon-size h-frotis-icon-size" /> Firmar y Validar Informe
            </button>
          ) : (
            <div className="flex items-center gap-2 text-frotis-success-text text-xs font-mono font-medium bg-frotis-success-surface px-3 py-1.5 rounded-sm border-frotis border-frotis-success-border">
              <CheckCircle2 className="w-frotis-icon-size h-frotis-icon-size" /> Hash SHA-256: 8f9b2...e4a1
              (Aprobado)
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
