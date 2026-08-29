import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
  type KeyboardEvent,
} from 'react';

import microscopeImage from '../assets/smear-microscope.jpg';
import { ApiError, api, type ScientificSample, type ScientificSubject } from '../services/api';

const NIH_SOURCE = 'nih_nlm_thin_blood_smears_pf';
const ACCEPTED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'tif', 'tiff'];
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/tiff'];
const MAX_UPLOAD_BYTES = 20_971_520;
const MAX_IMAGE_PIXELS = 100_000_000;

export type SmearUploadProps = {
  files: File[];
  previewUrl: string | null;
  busy: boolean;
  canAnalyze: boolean;
  onFilesChange: (files: File[]) => void;
  onAnalyze: (form: FormData) => Promise<void>;
};

const fileFormat = (file: File) => {
  if (file.type) return file.type.replace('image/', '').toUpperCase();
  const extension = file.name.split('.').pop();
  return extension ? extension.toUpperCase() : 'Desconocido';
};

const isAcceptedFile = (file: File) => {
  const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
  return ACCEPTED_TYPES.includes(file.type) || ACCEPTED_EXTENSIONS.includes(extension);
};

function Icon({ name }: { name: 'patient' | 'sample' | 'science' | 'upload' | 'play' | 'check' }) {
  const paths = {
    patient: <><circle cx="12" cy="8" r="3" /><path d="M5.5 20a6.5 6.5 0 0 1 13 0" /></>,
    sample: <><path d="M9 3h6M10 3v5l-4.5 8a3 3 0 0 0 2.6 4.5h7.8a3 3 0 0 0 2.6-4.5L14 8V3" /><path d="M8 15h8" /></>,
    science: <><path d="M9 3h6M10 3v5l-5 9a2.7 2.7 0 0 0 2.4 4h9.2a2.7 2.7 0 0 0 2.4-4l-5-9V3" /><path d="M8 15h8" /></>,
    upload: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" /><path d="M14 2v6h6M12 18v-6m-3 3 3-3 3 3" /></>,
    play: <path d="m9 7 8 5-8 5Z" />,
    check: <><circle cx="12" cy="12" r="9" /><path d="m8 12 2.5 2.5L16 9" /></>,
  };
  return <svg className="smear-setup__icon" viewBox="0 0 24 24" aria-hidden="true">{paths[name]}</svg>;
}

export function SmearUpload({
  files,
  previewUrl,
  busy,
  canAnalyze,
  onFilesChange,
  onAnalyze,
}: SmearUploadProps) {
  const [automaticSubject, setAutomaticSubject] = useState(true);
  const [subjectCode, setSubjectCode] = useState('');
  const [subject, setSubject] = useState<ScientificSubject | null>(null);
  const [subjectMessage, setSubjectMessage] = useState('');
  const [samples, setSamples] = useState<ScientificSample[]>([]);
  const [automaticSample, setAutomaticSample] = useState(true);
  const [sampleId, setSampleId] = useState('');
  const [origin, setOrigin] = useState<'manual' | 'nih' | 'external'>('manual');
  const [externalPatientId, setExternalPatientId] = useState('');
  const [externalSampleId, setExternalSampleId] = useState('');
  const [externalSystem, setExternalSystem] = useState('');
  const [inputKey, setInputKey] = useState(0);
  const [dragDepth, setDragDepth] = useState(0);
  const [fileError, setFileError] = useState('');
  const [dimensions, setDimensions] = useState<{ width: number; height: number } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!subject) {
      setSamples([]);
      setSampleId('');
      return;
    }
    api.getScientificSamples(subject.id)
      .then((response) => setSamples(response.items))
      .catch(() => setSamples([]));
  }, [subject]);

  useEffect(() => setDimensions(null), [previewUrl]);

  const selectedBytes = useMemo(
    () => files.reduce((total, file) => total + file.size, 0),
    [files],
  );

  async function lookup() {
    setSubject(null);
    setSubjectMessage('');
    try {
      const found = await api.lookupScientificSubject(subjectCode.trim());
      setSubject(found);
      setSubjectMessage(`Paciente ${found.subject_code} encontrado.`);
    } catch (error) {
      setSubjectMessage(
        error instanceof ApiError && error.status === 404
          ? 'No se encontró el paciente ingresado.'
          : 'No fue posible buscar el paciente.',
      );
    }
  }

  function selectFiles(nextFiles: File[]) {
    const invalid = nextFiles.find((file) => !isAcceptedFile(file));
    if (invalid) {
      setFileError(`“${invalid.name}” no es compatible. Use JPEG, PNG o TIFF.`);
      return;
    }
    const oversized = nextFiles.find((file) => file.size > MAX_UPLOAD_BYTES);
    if (oversized) {
      setFileError(`“${oversized.name}” supera el límite de 20 MiB por archivo.`);
      return;
    }
    setFileError('');
    onFilesChange(nextFiles);
  }

  function clearFiles() {
    onFilesChange([]);
    setFileError('');
    setInputKey((value) => value + 1);
  }

  function openPicker() {
    if (!busy) fileInput.current?.click();
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragDepth(0);
    if (!busy) selectFiles(Array.from(event.dataTransfer.files));
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openPicker();
    }
  }

  async function submit() {
    if (busy) return;
    const form = new FormData();
    files.forEach((file) => form.append('files', file));
    form.set('subject_mode', automaticSubject ? 'automatic_new' : 'existing');
    if (!automaticSubject) form.set('subject_code', subject?.subject_code ?? '');
    form.set('sample_mode', automaticSample ? 'automatic_new' : 'existing');
    if (!automaticSample) form.set('sample_id', sampleId);
    form.set(
      'acquisition_origin',
      origin === 'nih'
        ? 'research_dataset_import'
        : origin === 'external' ? 'external_capture_system' : 'manual_upload',
    );
    if (origin === 'nih') {
      form.set('source_system', NIH_SOURCE);
      form.set('external_patient_id', externalPatientId.trim());
      if (externalSampleId.trim()) form.set('external_sample_id', externalSampleId.trim());
    } else if (origin === 'external') {
      form.set('source_system', externalSystem.trim());
    }
    await onAnalyze(form);
  }

  const identityReady = automaticSubject || Boolean(subject);
  const sampleReady = automaticSample || Boolean(sampleId);
  const originReady = origin === 'nih'
    ? Boolean(externalPatientId.trim())
    : origin === 'external' ? Boolean(externalSystem.trim()) : true;
  const dimensionsReady = !dimensions || dimensions.width * dimensions.height <= MAX_IMAGE_PIXELS;
  const formReady = canAnalyze && identityReady && sampleReady && originReady
    && files.length > 0 && !fileError && dimensionsReady;
  const isDragging = dragDepth > 0;
  const disabledReason = busy
    ? 'El análisis ya se está iniciando; evita repetir el envío.'
    : !canAnalyze
      ? 'Tu rol no reúne todos los permisos requeridos para ejecutar el flujo.'
      : !identityReady
        ? 'Busca y selecciona un paciente válido.'
        : !sampleReady
          ? 'Selecciona una muestra válida.'
          : !originReady
            ? 'Completa los datos obligatorios del origen.'
            : !files.length
              ? 'Selecciona al menos una imagen compatible.'
              : fileError || (!dimensionsReady
                ? 'La imagen supera el límite de 100 megapíxeles.'
                : 'Listo para iniciar.');

  return (
    <section className="smear-setup" aria-labelledby="smear-setup-title">
      <header className="smear-setup__intro">
        <p>NUEVO WORKFLOW</p>
        <h2 id="smear-setup-title">Nuevo análisis de frotis</h2>
        <span>Identifica la muestra y carga los campos microscópicos. El sistema validará calidad, detectará células y aplicará el modelo productivo antes de la revisión experta.</span>
      </header>
      <div className="smear-setup__grid">
        <div className="smear-setup__sample-column">
          <section className="smear-setup__glass smear-setup__sample-panel">
            <h3>Datos de muestra</h3>

            <div className="smear-setup__field">
              <label htmlFor="smear-patient">ID PACIENTE</label>
              <div className="smear-setup__control">
                <Icon name="patient" />
                <input
                  id="smear-patient"
                  value={automaticSubject ? 'PAT-AUTOMÁTICO' : subjectCode}
                  disabled={automaticSubject || busy}
                  aria-describedby="smear-patient-help"
                  onChange={(event) => {
                    setSubjectCode(event.target.value);
                    setSubject(null);
                  }}
                />
                {!automaticSubject ? (
                  <button type="button" disabled={busy || !subjectCode.trim()} onClick={() => void lookup()}>
                    Buscar
                  </button>
                ) : null}
              </div>
              <label className="smear-setup__mode">
                <input
                  type="checkbox"
                  checked={automaticSubject}
                  disabled={busy}
                  onChange={(event) => {
                    setAutomaticSubject(event.target.checked);
                    setSubject(null);
                  }}
                />
                Crear paciente automáticamente
              </label>
              <small id="smear-patient-help">
                {automaticSubject ? 'Se asignará un ID pseudonimizado PAT-…' : subjectMessage || 'Busque un paciente existente.'}
              </small>
            </div>

            <div className="smear-setup__field">
              <label htmlFor="smear-sample">ID MUESTRA</label>
              <div className="smear-setup__control">
                <Icon name="sample" />
                <select
                  id="smear-sample"
                  value={automaticSample ? 'automatic' : sampleId}
                  disabled={busy || !identityReady}
                  onChange={(event) => setSampleId(event.target.value)}
                >
                  {automaticSample ? <option value="automatic">SMP-AUTOMÁTICA</option> : <option value="">Seleccione una muestra</option>}
                  {!automaticSample && samples.map((sample) => (
                    <option key={sample.id} value={sample.id}>{sample.sample_code}</option>
                  ))}
                </select>
              </div>
              <label className="smear-setup__mode">
                <input
                  type="checkbox"
                  checked={automaticSample}
                  disabled={busy}
                  onChange={(event) => setAutomaticSample(event.target.checked)}
                />
                Crear muestra automáticamente
              </label>
              <small>Se asociará al paciente seleccionado.</small>
            </div>

            <div className="smear-setup__field">
              <label htmlFor="smear-type">TIPO</label>
              <div className="smear-setup__control">
                <Icon name="science" />
                <select id="smear-type" value="peripheral-smear" disabled={busy}>
                  <option value="peripheral-smear">Frotis de sangre periférica</option>
                </select>
              </div>
            </div>

            <details className="smear-setup__origin">
              <summary>Modalidad u origen</summary>
              <label htmlFor="smear-origin">Origen de adquisición</label>
              <select
                id="smear-origin"
                value={origin}
                disabled={busy}
                onChange={(event) => setOrigin(event.target.value as typeof origin)}
              >
                <option value="manual">Carga manual</option>
                <option value="nih">Dataset NIH-NLM</option>
                <option value="external">Sistema externo</option>
              </select>
              {origin === 'nih' ? (
                <>
                  <label htmlFor="external-patient">ID externo de paciente</label>
                  <input id="external-patient" value={externalPatientId} disabled={busy} onChange={(event) => setExternalPatientId(event.target.value)} />
                  <label htmlFor="external-sample">ID externo de muestra (opcional)</label>
                  <input id="external-sample" value={externalSampleId} disabled={busy} onChange={(event) => setExternalSampleId(event.target.value)} />
                  <small>Este perfil espera 5 imágenes.</small>
                </>
              ) : null}
              {origin === 'external' ? (
                <>
                  <label htmlFor="external-system">Sistema externo</label>
                  <input id="external-system" value={externalSystem} disabled={busy} onChange={(event) => setExternalSystem(event.target.value)} />
                </>
              ) : null}
            </details>
          </section>

        </div>

        <div className="smear-setup__upload-column">
          <div className="smear-setup__upload-workspace">
            <div
              className="smear-setup__glass smear-setup__dropzone"
            data-state={busy ? 'uploading' : fileError ? 'invalid' : isDragging ? 'drag-active' : files.length ? 'selected' : 'idle'}
            role="button"
            tabIndex={busy ? -1 : 0}
            aria-disabled={busy}
            aria-describedby="smear-drop-help smear-file-feedback"
            onClick={(event) => {
              if (!(event.target instanceof HTMLButtonElement)) openPicker();
            }}
            onKeyDown={handleKeyDown}
            onDragEnter={(event) => {
              event.preventDefault();
              if (!busy) setDragDepth((value) => value + 1);
            }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={(event) => {
              event.preventDefault();
              setDragDepth((value) => Math.max(0, value - 1));
            }}
            onDrop={handleDrop}
            >
            <input
              ref={fileInput}
              key={inputKey}
              className="smear-setup__file-input"
              type="file"
              multiple
              disabled={busy}
              accept=".jpg,.jpeg,.png,.tif,.tiff,image/jpeg,image/png,image/tiff"
              tabIndex={-1}
              onChange={(event) => selectFiles(Array.from(event.target.files ?? []))}
            />
            <div className="smear-setup__glow" aria-hidden="true" />
            {previewUrl ? (
              <img
                className="smear-setup__preview"
                src={previewUrl}
                alt={`Vista previa de ${files[0]?.name ?? 'la imagen seleccionada'}`}
                onLoad={(event) => {
                  const next = {
                    width: event.currentTarget.naturalWidth,
                    height: event.currentTarget.naturalHeight,
                  };
                  setDimensions(next);
                  if (next.width * next.height > MAX_IMAGE_PIXELS) {
                    setFileError('La imagen supera el límite de 100 megapíxeles admitido por el backend.');
                  }
                }}
              />
            ) : (
              <img className="smear-setup__microscope" src={microscopeImage} alt="Microscopio clínico para análisis de frotis" />
            )}
            <div className="smear-setup__drop-copy">
              <span className="smear-setup__upload-icon"><Icon name="upload" /></span>
              <h3>{isDragging ? 'Suelte la imagen para cargarla' : 'Cargar imagen de frotis'}</h3>
              <p id="smear-drop-help">Arrastre y suelte una imagen aquí o selecciónela desde su equipo.</p>
              <small>JPEG, PNG o TIFF · máximo 20 MiB y 100 MP por archivo</small>
            </div>
            </div>

            <aside className="smear-setup__glass smear-setup__quality" aria-labelledby="smear-quality-title">
              <header>
                <div><p>VALIDACIÓN CLÁSICA</p><h3 id="smear-quality-title">Control de calidad</h3></div>
                <span className="smear-setup__file-count">{files.length} archivo{files.length === 1 ? '' : 's'}</span>
              </header>
              <p>Los criterios se confirmarán con las métricas reales del backend antes de detectar células.</p>
              <ul>
                {['Enfoque', 'Iluminación', 'Resolución', 'Artefactos'].map((criterion) => (
                  <li key={criterion} data-state="pending">
                    <span aria-hidden="true">•</span><strong>{criterion}</strong><em>Pendiente</em>
                  </li>
                ))}
              </ul>
              <small>Sin límite fijo de cantidad por lote manual. El perfil NIH requiere 5 imágenes.</small>
            </aside>
          </div>

          <div id="smear-file-feedback" className="smear-setup__feedback" aria-live="polite">
            {fileError ? <p role="alert">{fileError}</p> : null}
            {files[0] ? (
              <div className="smear-setup__file-details">
                <dl>
                  <div><dt>Archivo</dt><dd>{files[0].name}</dd></div>
                  <div><dt>Formato</dt><dd>{fileFormat(files[0])}</dd></div>
                  <div><dt>Dimensiones</dt><dd>{dimensions ? `${dimensions.width} × ${dimensions.height} px` : 'Leyendo…'}</dd></div>
                  <div><dt>Tamaño</dt><dd>{(selectedBytes / 1024 / 1024).toFixed(2)} MiB</dd></div>
                </dl>
                <div className="smear-setup__file-actions">
                  <button type="button" disabled={busy} onClick={openPicker}>Reemplazar</button>
                  <button type="button" disabled={busy} onClick={clearFiles}>Quitar</button>
                </div>
              </div>
            ) : null}
          </div>

          <footer className="smear-setup__actions">
            <p id="smear-analyze-reason">{disabledReason}</p>
            <button
              type="button"
              disabled={busy || !formReady}
              aria-describedby="smear-analyze-reason"
              aria-busy={busy}
              title={!formReady ? disabledReason : undefined}
              onClick={() => void submit()}
            >
              <Icon name="play" />
              {busy ? 'INICIANDO ANÁLISIS…' : 'INICIAR ANÁLISIS'}
            </button>
          </footer>
        </div>
      </div>
    </section>
  );
}
