import React, { useState } from "react";
import {
  X,
  Copy,
  Download,
  ExternalLink,
  Check,
  Code,
  FileText,
} from "lucide-react";

interface StandaloneHtmlModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const StandaloneHtmlModal: React.FC<StandaloneHtmlModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopy = async () => {
    try {
      const res = await fetch("/analisis-frotis-v2/visor-standalone.html");
      const html = await res.text();
      await navigator.clipboard.writeText(html);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      alert("No se pudo copiar el HTML. Puede descargar el archivo local.");
    }
  };

  const handleDownload = () => {
    const link = document.createElement("a");
    link.href = "/analisis-frotis-v2/visor-standalone.html";
    link.download = "visor-interactive-analysis.html";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="fixed inset-0 frotis-layer-modal flex items-center justify-center bg-frotis-overlay-base/60 backdrop-blur-xs p-frotis-component-padding select-none animate-in fade-in">
      <div className="bg-frotis-surface text-frotis-text-heading rounded-lg shadow-2xl border-frotis border-frotis-border w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-frotis-component-padding bg-frotis-surface-muted border-b border-frotis-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-frotis-selected-hover text-frotis-secondary-hover rounded-sm">
              <Code className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-frotis-text-primary">
                Archivo HTML Autocontenido (Requerimiento de Maqueta)
              </h3>
              <p className="text-frotis-label text-frotis-text-secondary">
                Demostración original local; no incluye los cambios temporales
                de esta sesión.
              </p>
            </div>
          </div>
          <button
            aria-label="Cerrar"
            onClick={onClose}
            className="p-1 text-frotis-text-muted hover:text-frotis-text-heading rounded-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-4 overflow-y-auto">
          <div className="p-frotis-component-padding bg-frotis-selected/60 border-frotis border-frotis-selected-border/80 rounded-md text-xs space-y-2">
            <div className="font-bold text-frotis-secondary-deep flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-frotis-success-accent"></span>
              Archivo Generado en el Workspace:
            </div>
            <p className="text-frotis-text-body leading-relaxed font-mono text-frotis-label">
              /public/analisis-frotis-v2/visor-standalone.html
            </p>
            <p className="text-frotis-text-control">
              Cumple con la especificación exacta de{" "}
              <strong>un único archivo HTML autocontenido</strong>, con la
              botonera morfológica interactiva, menús desplegables funcionales,
              zoom/pan del frotis, tabla diferencial y reportes.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <button
              onClick={handleCopy}
              className="p-3 border-frotis border-frotis-border hover:border-frotis-accent-soft hover:bg-frotis-selected/40 rounded-md flex flex-col items-center justify-center gap-2 text-xs font-semibold text-frotis-text-heading transition-colors"
            >
              {copied ? (
                <Check className="w-5 h-5 text-frotis-success" />
              ) : (
                <Copy className="w-5 h-5 text-frotis-secondary" />
              )}
              <span>{copied ? "¡Copiado!" : "Copiar Código HTML"}</span>
            </button>

            <button
              onClick={handleDownload}
              className="p-3 border-frotis border-frotis-border hover:border-frotis-accent-soft hover:bg-frotis-selected/40 rounded-md flex flex-col items-center justify-center gap-2 text-xs font-semibold text-frotis-text-heading transition-colors"
            >
              <Download className="w-5 h-5 text-frotis-secondary" />
              <span>Descargar .html</span>
            </button>

            <a
              href="/analisis-frotis-v2/visor-standalone.html"
              target="_blank"
              rel="noreferrer"
              className="p-3 border-frotis border-frotis-border hover:border-frotis-accent-soft hover:bg-frotis-selected/40 rounded-md flex flex-col items-center justify-center gap-2 text-xs font-semibold text-frotis-text-heading transition-colors"
            >
              <ExternalLink className="w-5 h-5 text-frotis-secondary" />
              <span>Abrir en Nueva Pestaña</span>
            </a>
          </div>

          <div className="border-frotis border-frotis-border rounded-md p-3 bg-frotis-surface-inverse text-frotis-border-strong text-frotis-label font-mono max-h-48 overflow-y-auto">
            <div className="text-frotis-success-marker mb-1">
              &lt;!-- Vista previa de estructura --&gt;
            </div>
            <div>&lt;!DOCTYPE html&gt;</div>
            <div>&lt;html lang="es"&gt;</div>
            <div>&nbsp;&nbsp;&lt;head&gt;</div>
            <div>
              &nbsp;&nbsp;&nbsp;&nbsp;&lt;style&gt;/* Estilos locales incluidos
              */&lt;/style&gt;
            </div>
            <div>
              &nbsp;&nbsp;&nbsp;&nbsp;&lt;title&gt;Visor - Digital
              Hematology Analysis Platform&lt;/title&gt;
            </div>
            <div>&nbsp;&nbsp;&lt;/head&gt;</div>
            <div>&nbsp;&nbsp;&lt;body&gt;</div>
            <div>
              &nbsp;&nbsp;&nbsp;&nbsp;&lt;header&gt;... botonera, selector de
              casos y opciones ...&lt;/header&gt;
            </div>
            <div>
              &nbsp;&nbsp;&nbsp;&nbsp;&lt;main&gt;... sidebar diferencial +
              botonera 42 celdas + frotis con pan/zoom ...&lt;/main&gt;
            </div>
            <div>&nbsp;&nbsp;&lt;/body&gt;</div>
            <div>&lt;/html&gt;</div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 bg-frotis-surface-muted border-t border-frotis-border flex justify-end">
          <button
            aria-label="Cerrar"
            onClick={onClose}
            className="px-4 py-1.5 bg-frotis-surface-inverse-raised hover:bg-frotis-surface-inverse-elevated text-frotis-text-inverse text-xs font-medium rounded-sm transition-colors"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
};
