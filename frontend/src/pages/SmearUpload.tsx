import { useEffect, useMemo, useState } from 'react';

import { ApiError, api } from '../services/api';

type Subject = { id: string; subject_code: string; status: string };
type Sample = { id: string; sample_code: string; status: string };
type UploadResult = {
  subject: Subject;
  sample: Sample;
  status: 'complete' | 'incomplete' | 'inconsistent';
  counts: { received: number; expected: number | null; ignored: number };
};

const NIH_SOURCE = 'nih_nlm_thin_blood_smears_pf';

export function SmearUpload() {
  const [automaticSubject, setAutomaticSubject] = useState(false);
  const [subjectCode, setSubjectCode] = useState('');
  const [subject, setSubject] = useState<Subject | null>(null);
  const [subjectMessage, setSubjectMessage] = useState('');
  const [samples, setSamples] = useState<Sample[]>([]);
  const [automaticSample, setAutomaticSample] = useState(true);
  const [sampleId, setSampleId] = useState('');
  const [origin, setOrigin] = useState<'manual' | 'nih' | 'external'>('manual');
  const [externalPatientId, setExternalPatientId] = useState('');
  const [externalSampleId, setExternalSampleId] = useState('');
  const [externalSystem, setExternalSystem] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

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
      setSubjectMessage(error instanceof ApiError && error.status === 404
        ? 'No se encontró el paciente ingresado.'
        : 'No fue posible buscar el paciente.');
    }
  }

  async function upload() {
    setBusy(true);
    setMessage('');
    try {
      const form = new FormData();
      files.forEach((file) => form.append('files', file));
      form.set('subject_mode', automaticSubject ? 'automatic_new' : 'existing');
      if (!automaticSubject) form.set('subject_code', subject?.subject_code ?? '');
      form.set('sample_mode', automaticSample ? 'automatic_new' : 'existing');
      if (!automaticSample) form.set('sample_id', sampleId);
      form.set('acquisition_origin', origin === 'nih'
        ? 'research_dataset_import'
        : origin === 'external' ? 'external_capture_system' : 'manual_upload');
      if (origin === 'nih') {
        form.set('source_system', NIH_SOURCE);
        form.set('external_patient_id', externalPatientId.trim());
        if (externalSampleId.trim()) form.set('external_sample_id', externalSampleId.trim());
      } else if (origin === 'external') {
        form.set('source_system', externalSystem.trim());
      }
      const result = await api.uploadMicroscopyImages(form);
      setSubject(result.subject);
      if (result.status === 'incomplete') {
        setMessage(`La muestra contiene ${result.counts.received} de ${result.counts.expected} imágenes esperadas.`);
      } else if (result.status === 'inconsistent') {
        setMessage('La muestra contiene más imágenes de las esperadas y requiere revisión.');
      } else {
        setMessage(`Se cargaron ${result.counts.received} imágenes para la muestra ${result.sample.sample_code} del paciente ${result.subject.subject_code}.`);
      }
      setFiles([]);
    } catch (error) {
      setMessage(error instanceof ApiError ? 'La carga fue rechazada por el backend. Revisa identidades, formato y tamaño.' : 'No fue posible completar la carga.');
    } finally {
      setBusy(false);
    }
  }

  const identityReady = automaticSubject || Boolean(subject);
  const sampleReady = automaticSample || Boolean(sampleId);
  const originReady = origin === 'nih' ? Boolean(externalPatientId.trim())
    : origin === 'external' ? Boolean(externalSystem.trim()) : true;

  return <section className="page smear-upload">
    <header className="page-title">
      <div><h1>Cargar imágenes de frotis</h1>
        <p>Asocia originales microscópicos a un paciente, una muestra y un único lote trazable.</p></div>
    </header>

    <div className="ingestion-grid">
      <fieldset className="ingestion-card">
        <legend>1. Paciente</legend>
        <p className="privacy-note">Utiliza un identificador pseudonimizado. No ingreses datos personales del paciente.</p>
        <label>ID de paciente
          <input value={subjectCode} disabled={automaticSubject}
            onChange={(event) => { setSubjectCode(event.target.value); setSubject(null); }} />
        </label>
        <button type="button" disabled={automaticSubject || !subjectCode.trim()} onClick={lookup}>Buscar</button>
        <label className="check-row"><input type="checkbox" checked={automaticSubject}
          onChange={(event) => { setAutomaticSubject(event.target.checked); setSubject(null); }} />
          Crear nuevo paciente automáticamente</label>
        {automaticSubject ? <p>Capstone generará un nuevo ID pseudonimizado.</p> : null}
        {subjectMessage ? <p role="status">{subjectMessage}</p> : null}
      </fieldset>

      <fieldset className="ingestion-card" disabled={!identityReady}>
        <legend>2. Muestra</legend>
        <label>Muestra existente
          <select value={sampleId} disabled={automaticSample} onChange={(event) => setSampleId(event.target.value)}>
            <option value="">Selecciona una muestra</option>
            {samples.map((sample) => <option key={sample.id} value={sample.id}>{sample.sample_code}</option>)}
          </select>
        </label>
        <label className="check-row"><input type="checkbox" checked={automaticSample}
          onChange={(event) => setAutomaticSample(event.target.checked)} />
          Crear nueva muestra automáticamente</label>
        {automaticSample ? <p>Capstone generará una nueva muestra para este paciente.</p> : null}
      </fieldset>

      <fieldset className="ingestion-card">
        <legend>3. Origen</legend>
        <label>Modalidad
          <select value={origin} onChange={(event) => setOrigin(event.target.value as typeof origin)}>
            <option value="manual">Carga manual</option>
            <option value="nih">Dataset NIH-NLM</option>
            <option value="external">Sistema externo</option>
          </select>
        </label>
        {origin === 'nih' ? <>
          <label>ID externo de paciente<input value={externalPatientId} onChange={(event) => setExternalPatientId(event.target.value)} /></label>
          <label>ID externo de muestra (opcional)<input value={externalSampleId} onChange={(event) => setExternalSampleId(event.target.value)} /></label>
          <p>Se esperan 5 imágenes para este perfil.</p>
        </> : null}
        {origin === 'external' ? <label>Sistema externo<input value={externalSystem} onChange={(event) => setExternalSystem(event.target.value)} /></label> : null}
      </fieldset>

      <fieldset className="ingestion-card">
        <legend>4. Archivos</legend>
        <label>Imágenes JPEG, PNG o TIFF
          <input type="file" multiple accept=".jpg,.jpeg,.png,.tif,.tiff,image/jpeg,image/png,image/tiff"
            onChange={(event) => setFiles(Array.from(event.target.files ?? []))} />
        </label>
        <p>{origin === 'nih' ? `${files.length} de 5 imágenes seleccionadas.` : `${files.length} imágenes seleccionadas.`}</p>
        <p>{(selectedBytes / 1024 / 1024).toFixed(2)} MiB en total.</p>
        <ul className="file-list">{files.map((file) => <li key={`${file.name}-${file.lastModified}`}>
          <span>{file.name}</span><small>{(file.size / 1024).toFixed(1)} KiB</small>
        </li>)}</ul>
      </fieldset>
    </div>

    <div className="ingestion-submit">
      <button type="button" disabled={busy || !identityReady || !sampleReady || !originReady || files.length === 0}
        onClick={upload}>{busy ? 'Cargando originales…' : 'Cargar imágenes'}</button>
      {message ? <p role="status">{message}</p> : null}
    </div>
  </section>;
}
