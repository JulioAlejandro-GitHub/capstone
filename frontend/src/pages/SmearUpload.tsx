import { useEffect, useMemo, useState } from 'react';

import { ApiError, api, type ScientificSample, type ScientificSubject } from '../services/api';

const NIH_SOURCE = 'nih_nlm_thin_blood_smears_pf';

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

  function clearFiles() {
    onFilesChange([]);
    setInputKey((value) => value + 1);
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
  const formReady = (
    canAnalyze
    && identityReady
    && sampleReady
    && originReady
    && files.length > 0
  );

  return (
    <section className="smear-setup" aria-labelledby="smear-setup-title">
      <div className="smear-setup-copy">
        <p className="workflow-kicker">Nuevo análisis</p>
        <h2 id="smear-setup-title">Configura la muestra y selecciona la imagen</h2>
        <p>
          El archivo se mostrará de inmediato. La carga, el control técnico y la detección
          se ejecutarán como una sola acción manual trazable.
        </p>
      </div>

      <div className="smear-setup-layout">
        <div className="ingestion-grid smear-ingestion-grid">
          <fieldset className="ingestion-card">
            <legend><span>1</span> Paciente</legend>
            <p className="privacy-note">
              Usa un identificador pseudonimizado. No ingreses datos personales.
            </p>
            <label>
              Código de paciente
              <div className="workflow-inline-field">
                <input
                  value={subjectCode}
                  disabled={automaticSubject || busy}
                  placeholder="Ej. SUB-…"
                  onChange={(event) => {
                    setSubjectCode(event.target.value);
                    setSubject(null);
                  }}
                />
                <button
                  type="button"
                  disabled={automaticSubject || busy || !subjectCode.trim()}
                  onClick={() => void lookup()}
                >
                  Buscar
                </button>
              </div>
            </label>
            <label className="check-row">
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
            <p className="workflow-field-note">
              {automaticSubject
                ? 'Capstone generará un código pseudonimizado.'
                : subjectMessage || 'Busca y confirma un paciente existente.'}
            </p>
          </fieldset>

          <fieldset className="ingestion-card" disabled={!identityReady || busy}>
            <legend><span>2</span> Muestra</legend>
            <label>
              Muestra existente
              <select
                value={sampleId}
                disabled={automaticSample || busy}
                onChange={(event) => setSampleId(event.target.value)}
              >
                <option value="">Selecciona una muestra</option>
                {samples.map((sample) => (
                  <option key={sample.id} value={sample.id}>{sample.sample_code}</option>
                ))}
              </select>
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={automaticSample}
                disabled={busy}
                onChange={(event) => setAutomaticSample(event.target.checked)}
              />
              Crear muestra automáticamente
            </label>
            <p className="workflow-field-note">
              {automaticSample
                ? 'Se generará una muestra asociada al paciente.'
                : 'Selecciona una muestra activa.'}
            </p>
          </fieldset>

          <fieldset className="ingestion-card">
            <legend><span>3</span> Origen</legend>
            <label>
              Modalidad
              <select
                value={origin}
                disabled={busy}
                onChange={(event) => setOrigin(event.target.value as typeof origin)}
              >
                <option value="manual">Carga manual</option>
                <option value="nih">Dataset NIH-NLM</option>
                <option value="external">Sistema externo</option>
              </select>
            </label>
            {origin === 'nih' ? (
              <>
                <label>
                  ID externo de paciente
                  <input
                    value={externalPatientId}
                    disabled={busy}
                    onChange={(event) => setExternalPatientId(event.target.value)}
                  />
                </label>
                <label>
                  ID externo de muestra (opcional)
                  <input
                    value={externalSampleId}
                    disabled={busy}
                    onChange={(event) => setExternalSampleId(event.target.value)}
                  />
                </label>
                <p className="workflow-field-note">Este perfil espera 5 imágenes.</p>
              </>
            ) : null}
            {origin === 'external' ? (
              <label>
                Sistema externo
                <input
                  value={externalSystem}
                  disabled={busy}
                  onChange={(event) => setExternalSystem(event.target.value)}
                />
              </label>
            ) : null}
          </fieldset>

          <fieldset className="ingestion-card workflow-file-card">
            <legend><span>4</span> Imagen</legend>
            <label className="workflow-file-picker">
              <span>{files.length ? 'Reemplazar imágenes' : 'Seleccionar imágenes'}</span>
              <small>JPEG, PNG o TIFF</small>
              <input
                key={inputKey}
                type="file"
                multiple
                disabled={busy}
                accept=".jpg,.jpeg,.png,.tif,.tiff,image/jpeg,image/png,image/tiff"
                onChange={(event) => onFilesChange(Array.from(event.target.files ?? []))}
              />
            </label>
            {files.length ? (
              <div className="workflow-file-summary">
                <div>
                  <strong>{files.length}</strong>
                  <span>{files.length === 1 ? 'imagen' : 'imágenes'}</span>
                </div>
                <div>
                  <strong>{(selectedBytes / 1024 / 1024).toFixed(2)}</strong>
                  <span>MiB</span>
                </div>
                <div>
                  <strong>{fileFormat(files[0])}</strong>
                  <span>formato inicial</span>
                </div>
              </div>
            ) : <p className="workflow-empty-copy">No hay imagen seleccionada.</p>}
            <ul className="file-list workflow-file-list">
              {files.map((file) => (
                <li key={`${file.name}-${file.lastModified}`}>
                  <span>{file.name}</span>
                  <small>{(file.size / 1024).toFixed(1)} KiB</small>
                </li>
              ))}
            </ul>
            {files.length ? (
              <button className="workflow-remove-file" type="button" disabled={busy} onClick={clearFiles}>
                Quitar selección
              </button>
            ) : null}
          </fieldset>
        </div>

        <aside className={`workflow-local-preview${previewUrl ? ' has-image' : ''}`}>
          <div className="workflow-preview-heading">
            <span>Vista previa local</span>
            {files[0] ? <small>{fileFormat(files[0])}</small> : null}
          </div>
          <div className="workflow-preview-frame">
            {previewUrl
              ? <img src={previewUrl} alt={`Vista previa de ${files[0]?.name ?? 'la imagen seleccionada'}`} />
              : (
                <div className="workflow-preview-empty">
                  <span aria-hidden="true">＋</span>
                  <strong>Selecciona una imagen</strong>
                  <p>La vista previa aparecerá aquí antes de cargarla.</p>
                </div>
              )}
          </div>
          {files[0] ? (
            <dl className="workflow-preview-facts">
              <div><dt>Archivo</dt><dd>{files[0].name}</dd></div>
              <div><dt>Tamaño</dt><dd>{(files[0].size / 1024 / 1024).toFixed(2)} MiB</dd></div>
              <div><dt>Formato</dt><dd>{fileFormat(files[0])}</dd></div>
              <div><dt>Cantidad</dt><dd>{files.length}</dd></div>
            </dl>
          ) : null}
        </aside>
      </div>

      <footer className="ingestion-submit workflow-submit">
        <div>
          <strong>El quality gate no se omitirá.</strong>
          <span>Advertencias y fallos detienen el avance.</span>
        </div>
        <button
          type="button"
          disabled={busy || !formReady}
          title={canAnalyze ? undefined : 'Tu rol no permite ejecutar el workflow completo.'}
          onClick={() => void submit()}
        >
          {busy ? 'Procesando…' : 'Cargar y analizar'}
        </button>
      </footer>
    </section>
  );
}
