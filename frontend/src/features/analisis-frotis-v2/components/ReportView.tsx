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
    <div className="flex-1 bg-slate-100 overflow-y-auto p-6 flex justify-center custom-scrollbar">
      <div className="w-full max-w-4xl bg-white shadow-lg border border-slate-200 rounded-sm p-8 text-slate-800 space-y-6">
        {/* Report Top Header */}
        <div className="flex items-center justify-between border-b-2 border-[#4D58A4] pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-md bg-[#4D58A4] flex items-center justify-center text-white">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                INFORME DE MORFOLOGÍA HEMATOLÓGICA DIGITAL
              </h1>
              <p className="text-xs text-slate-500 font-mono">
                Sistema Visor Full-Field Digital Morphology Analyzer
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => window.print()}
              className="px-3 py-1.5 border border-slate-300 hover:bg-slate-50 rounded-sm text-xs font-medium text-slate-700 flex items-center gap-1.5 transition-colors"
            >
              <Printer className="w-4 h-4" /> Imprimir
            </button>
            <button
              onClick={() =>
                alert(
                  "Demostración: no se genera un PDF clínico. Use Imprimir para guardar una copia local.",
                )
              }
              className="px-3 py-1.5 bg-[#4D58A4] hover:bg-[#3f498c] text-white rounded-sm text-xs font-medium flex items-center gap-1.5 transition-colors shadow-xs"
            >
              <Download className="w-4 h-4" /> Exportar PDF
            </button>
          </div>
        </div>

        {/* Patient and Specimen Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-slate-50 border border-slate-200 rounded-sm text-xs">
          <div>
            <span className="text-slate-400 block font-medium">Paciente</span>
            <span className="font-semibold text-slate-900 text-sm">
              {activeCase.patient.name}
            </span>
          </div>
          <div>
            <span className="text-slate-400 block font-medium">
              Edad / Sexo
            </span>
            <span className="font-semibold text-slate-800">
              {activeCase.patient.age} años / {activeCase.patient.gender}
            </span>
          </div>
          <div>
            <span className="text-slate-400 block font-medium">
              Nº Caso / MRN
            </span>
            <span className="font-mono font-semibold text-indigo-700">
              {activeCase.displayId}
            </span>
          </div>
          <div>
            <span className="text-slate-400 block font-medium">
              Fecha Colección
            </span>
            <span className="font-mono text-slate-700">
              {activeCase.patient.collectionDate}
            </span>
          </div>
          <div className="col-span-2">
            <span className="text-slate-400 block font-medium">
              Tipo de Muestra
            </span>
            <span className="text-slate-700">
              {activeCase.patient.sampleType}
            </span>
          </div>
          <div className="col-span-2">
            <span className="text-slate-400 block font-medium">
              Médico Solicitante
            </span>
            <span className="text-slate-700">
              {activeCase.patient.orderingPhysician}
            </span>
          </div>
        </div>

        {/* Differential Leukocyte Count Breakdown */}
        <div>
          <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-2 flex items-center justify-between">
            <span>Fórmula Leucocitaria Digital (500 Células Nucleadas)</span>
            <span className="text-xs text-slate-500 font-normal">
              Área escaneada: {activeCase.scanSizeCm2} cm²
            </span>
          </h2>
          <div className="border border-slate-200 rounded-sm overflow-hidden text-xs">
            <table className="w-full text-left">
              <thead className="bg-slate-100 text-slate-600 border-b border-slate-200 font-semibold">
                <tr>
                  <th className="py-2 px-3">Célula / Linaje</th>
                  <th className="py-2 px-3 text-right">Recuento</th>
                  <th className="py-2 px-3 text-right">Porcentaje (%)</th>
                  <th className="py-2 px-3 text-right">Rango Referencia</th>
                  <th className="py-2 px-3 text-center">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {activeCase.categories
                  .filter((c) => c.count > 0)
                  .map((cat) => {
                    const isHigh =
                      cat.name === "Promyelocyte" || cat.name === "Blast";
                    return (
                      <tr
                        key={cat.name}
                        className={isHigh ? "bg-amber-50/70 font-semibold" : ""}
                      >
                        <td className="py-1.5 px-3 font-sans text-slate-800">
                          {cat.name}
                        </td>
                        <td className="py-1.5 px-3 text-right">{cat.count}</td>
                        <td className="py-1.5 px-3 text-right text-indigo-700 font-bold">
                          {cat.percentage}%
                        </td>
                        <td className="py-1.5 px-3 text-right text-slate-500">
                          {cat.referenceRange || "--"}
                        </td>
                        <td className="py-1.5 px-3 text-center">
                          {isHigh ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] bg-rose-100 text-rose-700 font-sans font-semibold">
                              ANÓMALO ELEVADO
                            </span>
                          ) : (
                            <span className="text-emerald-600 text-[10px] font-sans">
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
          <label className="block text-sm font-bold text-slate-800 uppercase tracking-wider">
            Impresión Diagnóstica y Comentarios del Hematopatólogo
          </label>
          <textarea
            rows={4}
            value={diagnosticImpression}
            onChange={(e) => setDiagnosticImpression(e.target.value)}
            disabled={isSigned}
            className="w-full p-3 border border-slate-300 rounded-sm text-xs leading-relaxed text-slate-800 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 bg-white disabled:bg-slate-50"
          />
        </div>

        {/* Digital Signature & Sign-off Section */}
        <div className="pt-4 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center ${
                isSigned
                  ? "bg-emerald-100 text-emerald-700"
                  : "bg-amber-100 text-amber-700"
              }`}
            >
              {isSigned ? (
                <ShieldCheck className="w-6 h-6" />
              ) : (
                <AlertTriangle className="w-5 h-5" />
              )}
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-900">
                {isSigned
                  ? "Informe Firmado Digitalmente"
                  : "Pendiente de Validación y Firma"}
              </div>
              <div className="text-[11px] text-slate-500">
                Validador: {pathologistName}
              </div>
            </div>
          </div>

          {!isSigned ? (
            <button
              onClick={handleSign}
              className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs rounded-sm shadow-sm flex items-center gap-2 transition-colors cursor-pointer"
            >
              <UserCheck className="w-4 h-4" /> Firmar y Validar Informe
            </button>
          ) : (
            <div className="flex items-center gap-2 text-emerald-700 text-xs font-mono font-medium bg-emerald-50 px-3 py-1.5 rounded-sm border border-emerald-200">
              <CheckCircle2 className="w-4 h-4" /> Hash SHA-256: 8f9b2...e4a1
              (Aprobado)
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
