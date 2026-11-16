import { Upload, X } from 'lucide-react';
import { useRef, useState, type DragEvent } from 'react';

/** Formatos y límites efectivamente soportados por la ingestión existente. */
const ACCEPTED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'tif', 'tiff'];
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/tiff'];
const MAX_UPLOAD_BYTES = 20_971_520;

const isAccepted = (file: File) => {
  const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
  return ACCEPTED_TYPES.includes(file.type) || ACCEPTED_EXTENSIONS.includes(extension);
};
const megabytes = (bytes: number) => `${(bytes / 1_048_576).toFixed(1)} MiB`;

/**
 * Pantalla 1 — Incorporar imágenes de frotis.
 * Vive dentro del mismo workspace que después permite examinar el frotis y
 * delega la carga en el workflow de ingestión existente (`onStart`).
 */
export function IntakeStage({
  files,
  busy,
  canStart,
  missingPermissions,
  errorMessage,
  onFilesChange,
  onStart,
}: {
  files: File[];
  busy: boolean;
  canStart: boolean;
  missingPermissions: readonly string[];
  errorMessage: string | null;
  onFilesChange: (files: File[]) => void;
  onStart: (form: FormData) => Promise<void>;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [dragDepth, setDragDepth] = useState(0);
  const [fileError, setFileError] = useState('');

  const select = (next: File[]) => {
    if (!next.length) return;
    const invalid = next.find((file) => !isAccepted(file));
    if (invalid) {
      setFileError(`«${invalid.name}» no es compatible. Usa JPEG, PNG o TIFF.`);
      return;
    }
    const oversized = next.find((file) => file.size > MAX_UPLOAD_BYTES);
    if (oversized) {
      setFileError(`«${oversized.name}» supera el límite de 20 MiB por archivo.`);
      return;
    }
    setFileError('');
    onFilesChange(next);
  };
  const clear = () => {
    setFileError('');
    onFilesChange([]);
    if (input.current) input.current.value = '';
  };
  const drop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragDepth(0);
    if (!busy) select(Array.from(event.dataTransfer.files));
  };
  const start = async () => {
    if (busy || !canStart || !files.length) return;
    // Mismo contrato de formulario que el workflow existente de carga.
    const form = new FormData();
    files.forEach((file) => form.append('files', file));
    form.set('subject_mode', 'automatic_new');
    form.set('sample_mode', 'automatic_new');
    form.set('acquisition_origin', 'manual_upload');
    await onStart(form);
  };

  const ready = canStart && files.length > 0 && !fileError && !busy;
  return (
    <div
      className="frotis-v3-intake"
      data-dragging={dragDepth > 0 ? 'true' : 'false'}
      onDragEnter={(event) => { event.preventDefault(); setDragDepth((depth) => depth + 1); }}
      onDragLeave={() => setDragDepth((depth) => Math.max(0, depth - 1))}
      onDragOver={(event) => event.preventDefault()}
      onDrop={drop}
    >
      <div className="frotis-v3-intake-target">
        <Upload className="frotis-v3-intake-icon" aria-hidden="true" />
        <h2>Incorporar imágenes de frotis</h2>
        <p>Arrastra las imágenes al campo del microscopio o selecciónalas desde tu equipo.</p>
        <p className="frotis-v3-intake-limits">JPEG, PNG o TIFF · hasta 20 MiB por archivo</p>

        <input
          ref={input}
          id="frotis-v3-intake-files"
          className="frotis-v3-visually-hidden"
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.tif,.tiff,image/jpeg,image/png,image/tiff"
          disabled={busy}
          onChange={(event) => select(Array.from(event.target.files ?? []))}
        />
        <div className="frotis-v3-intake-actions">
          <button
            type="button"
            className="frotis-v3-button"
            disabled={busy}
            onClick={() => input.current?.click()}
          >
            {files.length ? 'Cambiar selección' : 'Seleccionar imágenes'}
          </button>
          <button
            type="button"
            className="frotis-v3-button frotis-v3-button--primary"
            disabled={!ready}
            onClick={() => void start()}
          >
            Incorporar y analizar
          </button>
        </div>

        {files.length ? (
          <div className="frotis-v3-intake-files">
            <div className="frotis-v3-intake-files-head">
              <strong>{files.length === 1 ? '1 imagen seleccionada' : `${files.length} imágenes seleccionadas`}</strong>
              <button type="button" className="frotis-v3-icon-button" onClick={clear} disabled={busy} aria-label="Quitar selección">
                <X aria-hidden="true" />
              </button>
            </div>
            <ul>
              {files.map((file) => (
                <li key={`${file.name}:${file.size}:${file.lastModified}`}>
                  <span>{file.name}</span>
                  <small>{megabytes(file.size)}</small>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {fileError ? <p className="frotis-v3-intake-error" role="alert">{fileError}</p> : null}
        {errorMessage ? <p className="frotis-v3-intake-error" role="alert">{errorMessage}</p> : null}
        {!canStart ? (
          <p className="frotis-v3-intake-error" role="alert">
            Tu rol no reúne los permisos para iniciar un análisis. Faltan: {missingPermissions.join(', ')}.
          </p>
        ) : null}

        <p className="frotis-v3-intake-restriction" role="note">
          En esta fase el microscopio registra paciente y muestra nuevos de forma automática, con
          origen «carga manual». Asociar las imágenes a un paciente o muestra existente, o a un
          origen externo, sigue disponible en «Analizar imagen».
        </p>
      </div>
    </div>
  );
}
