import React from "react";
import {
  X,
  FileText,
  FileSpreadsheet,
  Download,
  Image,
  Check,
  FileCode,
} from "lucide-react";
import { ClinicalCase } from "../types/visor";

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeCase: ClinicalCase;
  onOpenStandaloneHtml: () => void;
}

export const ExportModal: React.FC<ExportModalProps> = ({
  isOpen,
  onClose,
  activeCase,
  onOpenStandaloneHtml,
}) => {
  if (!isOpen) return null;

  const downloadCsv = () => {
    let csv = "Categoria,Recuento,Porcentaje,RangoReferencia\n";
    activeCase.categories.forEach((c) => {
      csv += `"${c.name}",${c.count},${c.percentage}%,"${c.referenceRange || ""}"\n`;
    });
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `visor_${activeCase.id}_differential.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 select-none animate-in fade-in">
      <div className="bg-white text-slate-800 rounded-lg shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden">
        <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-bold text-sm text-slate-900">
            Exportar Datos del Caso {activeCase.displayId}
          </h3>
          <button
            aria-label="Cerrar"
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-800 rounded-md"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-3">
          {/* Option 1: Standalone HTML (User's special request!) */}
          <div
            onClick={() => {
              onClose();
              onOpenStandaloneHtml();
            }}
            className="p-3.5 border-2 border-indigo-200 bg-indigo-50/50 hover:bg-indigo-50 rounded-md cursor-pointer transition-colors flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-600 text-white rounded-md">
                <FileCode className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-bold text-indigo-950">
                  Archivo HTML Único Autocontenido
                </div>
                <div className="text-[11px] text-slate-600">
                  Un único archivo .html portable con estilos, botonera
                  interactiva y JavaScript incrustado.
                </div>
              </div>
            </div>
            <span className="text-xs font-semibold text-indigo-600 px-2 py-1 bg-white rounded-sm border border-indigo-200 shadow-xs">
              Ver / Descargar
            </span>
          </div>

          {/* Option 2: CSV Data */}
          <div
            onClick={downloadCsv}
            className="p-3 border border-slate-200 hover:border-slate-300 hover:bg-slate-50 rounded-md cursor-pointer transition-colors flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-100 text-emerald-700 rounded-md">
                <FileSpreadsheet className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-bold text-slate-900">
                  Recuento Diferencial en CSV (Excel)
                </div>
                <div className="text-[11px] text-slate-500">
                  Datos tabulares de las 500 células nucleadas clasificadas por
                  IA y patólogo.
                </div>
              </div>
            </div>
            <Download className="w-4 h-4 text-slate-400" />
          </div>

          {/* Option 3: PDF Pathology Report */}
          <div
            onClick={() => window.print()}
            className="p-3 border border-slate-200 hover:border-slate-300 hover:bg-slate-50 rounded-md cursor-pointer transition-colors flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-rose-100 text-rose-700 rounded-md">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-bold text-slate-900">
                  Imprimir demostración / Guardar PDF
                </div>
                <div className="text-[11px] text-slate-500">
                  Copia local de la vista actual, sin firma digital ni validez
                  clínica.
                </div>
              </div>
            </div>
            <Download className="w-4 h-4 text-slate-400" />
          </div>
        </div>

        <div className="p-3 bg-slate-50 border-t border-slate-200 flex justify-end">
          <button
            aria-label="Cerrar"
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-medium rounded-sm transition-colors"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};
