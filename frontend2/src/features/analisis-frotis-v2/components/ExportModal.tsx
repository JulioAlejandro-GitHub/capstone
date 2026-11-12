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
    <div className="fixed inset-0 frotis-layer-modal flex items-center justify-center bg-frotis-overlay-base/60 backdrop-blur-xs p-frotis-component-padding select-none animate-in fade-in">
      <div className="bg-frotis-surface text-frotis-text-heading rounded-lg shadow-2xl border-frotis border-frotis-border w-full max-w-lg overflow-hidden">
        <div className="p-frotis-component-padding bg-frotis-surface-muted border-b border-frotis-border flex items-center justify-between">
          <h3 className="font-bold text-sm text-frotis-text-primary">
            Exportar Datos del Caso {activeCase.displayId}
          </h3>
          <button
            aria-label="Cerrar"
            onClick={onClose}
            className="p-1 text-frotis-text-muted hover:text-frotis-text-heading rounded-md"
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
            className="p-3.5 border-2 border-frotis-selected-border bg-frotis-selected/50 hover:bg-frotis-selected rounded-md cursor-pointer transition-colors flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-frotis-secondary text-frotis-text-inverse rounded-md">
                <FileCode className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-bold text-frotis-secondary-deep">
                  Archivo HTML Único Autocontenido
                </div>
                <div className="text-frotis-label text-frotis-text-control">
                  Un único archivo .html portable con estilos, botonera
                  interactiva y JavaScript incrustado.
                </div>
              </div>
            </div>
            <span className="text-xs font-semibold text-frotis-secondary px-2 py-1 bg-frotis-surface rounded-sm border-frotis border-frotis-selected-border shadow-xs">
              Ver / Descargar
            </span>
          </div>

          {/* Option 2: CSV Data */}
          <div
            onClick={downloadCsv}
            className="p-3 border-frotis border-frotis-border hover:border-frotis-border-strong hover:bg-frotis-surface-muted rounded-md cursor-pointer transition-colors flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-frotis-success-subtle text-frotis-success-text rounded-md">
                <FileSpreadsheet className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-bold text-frotis-text-primary">
                  Recuento Diferencial en CSV (Excel)
                </div>
                <div className="text-frotis-label text-frotis-text-secondary">
                  Datos tabulares de las 500 células nucleadas clasificadas por
                  IA y patólogo.
                </div>
              </div>
            </div>
            <Download className="w-frotis-icon-size h-frotis-icon-size text-frotis-text-muted" />
          </div>

          {/* Option 3: PDF Pathology Report */}
          <div
            onClick={() => window.print()}
            className="p-3 border-frotis border-frotis-border hover:border-frotis-border-strong hover:bg-frotis-surface-muted rounded-md cursor-pointer transition-colors flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-frotis-error-subtle text-frotis-error-text rounded-md">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-bold text-frotis-text-primary">
                  Imprimir demostración / Guardar PDF
                </div>
                <div className="text-frotis-label text-frotis-text-secondary">
                  Copia local de la vista actual, sin firma digital ni validez
                  clínica.
                </div>
              </div>
            </div>
            <Download className="w-frotis-icon-size h-frotis-icon-size text-frotis-text-muted" />
          </div>
        </div>

        <div className="p-3 bg-frotis-surface-muted border-t border-frotis-border flex justify-end">
          <button
            aria-label="Cerrar"
            onClick={onClose}
            className="px-4 py-1.5 bg-frotis-border hover:bg-frotis-border-strong text-frotis-text-body text-xs font-medium rounded-sm transition-colors"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};
