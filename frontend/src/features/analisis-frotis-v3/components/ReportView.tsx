import type { MicroscopeAnalysis } from '../adapters/analysisModel';
import { stageLabel } from '../adapters/analysisModel';
import { formatProbability, reviewLabel } from '../adapters/cellLayer';
import type { ReportFinding, ReportFindingsState } from '../hooks/useReportFindings';

const OUTCOME_LABEL: Record<string, string> = {
  suspicious_cells_detected: 'Se detectaron células sospechosas',
  no_suspicious_cells_detected: 'No se detectaron células sospechosas',
  inconclusive: 'No concluyente',
};
const number = (value: number | null | undefined) => (value == null ? '—' : value.toLocaleString('es-CL'));
const date = (value: string | null) => {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? '—' : parsed.toLocaleString('es-CL');
};

/**
 * REPORT: superficie documental con los resultados persistidos del análisis.
 * Solo presenta valores entregados por el backend; lo ausente se muestra como «—».
 */
export function ReportView({
  analysis,
  findings,
  onOpenFinding,
}: {
  analysis: MicroscopeAnalysis;
  findings: ReportFindingsState;
  onOpenFinding: (finding: ReportFinding) => void;
}) {
  const { detection, classification } = analysis;
  return (
    <article className="frotis-v3-report" aria-label="Reporte del análisis">
      <header>
        <h2>Reporte del análisis {analysis.runCode ?? ''}</h2>
        <p>
          Paciente {analysis.subjectCode ?? '—'} · Muestra {analysis.sampleCode ?? '—'} · Frotis {analysis.slideCode ?? '—'}
        </p>
        <p>Estado: {stageLabel(analysis.stage)} · Creado: {date(analysis.createdAt)}</p>
      </header>

      <section aria-labelledby="frotis-v3-report-summary">
        <h3 id="frotis-v3-report-summary">Resumen</h3>
        {classification?.outcome ? (
          <p className="frotis-v3-report-outcome">{OUTCOME_LABEL[classification.outcome] ?? classification.outcome}</p>
        ) : null}
        <dl className="frotis-v3-report-stats">
          <div><dt>Imágenes</dt><dd>{number(analysis.images.length)}</dd></div>
          <div><dt>Células detectadas</dt><dd>{number(detection?.detectionCount)}</dd></div>
          <div><dt>Detecciones revisadas</dt><dd>{number(detection?.reviewedCount)}</dd></div>
          <div><dt>Pendientes de revisión</dt><dd>{number(detection?.pendingReviewCount)}</dd></div>
          <div><dt>Células clasificadas</dt><dd>{number(classification?.classifiedCount)}</dd></div>
          <div><dt>Candidatas parasitadas</dt><dd>{number(classification?.parasitizedCandidateCount)}</dd></div>
          <div><dt>No infectadas</dt><dd>{number(classification?.uninfectedCandidateCount)}</dd></div>
          <div><dt>Cercanas al umbral</dt><dd>{number(classification?.nearThresholdCount)}</dd></div>
          <div><dt>Predicciones fallidas</dt><dd>{number(classification?.failedPredictionCount)}</dd></div>
          <div>
            <dt>Fracción de candidatas</dt>
            <dd>{formatProbability(classification?.parasitizedFraction ?? null)}</dd>
          </div>
        </dl>
        {classification ? (
          <p>
            Modelo: {classification.modelName ?? '—'}{classification.modelVersion ? ` ${classification.modelVersion}` : ''}
          </p>
        ) : <p>Este análisis no tiene clasificación celular registrada.</p>}
        {!detection ? <p>Este análisis no tiene detección celular registrada.</p> : null}
      </section>

      <section aria-labelledby="frotis-v3-report-images">
        <h3 id="frotis-v3-report-images">Imágenes</h3>
        <table>
          <thead><tr><th>#</th><th>Archivo</th><th>Dimensiones</th><th>Células detectadas</th></tr></thead>
          <tbody>
            {analysis.images.map((image, index) => (
              <tr key={image.id}>
                <td>{index + 1}</td>
                <td>{image.name}</td>
                <td>{image.widthPx && image.heightPx ? `${image.widthPx} × ${image.heightPx} px` : '—'}</td>
                <td>{number(image.detectionCount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section aria-labelledby="frotis-v3-report-findings">
        <h3 id="frotis-v3-report-findings">Hallazgos: candidatas parasitadas y células cercanas al umbral</h3>
        {!classification ? <p>Sin clasificación no hay hallazgos que listar.</p> : null}
        {findings.status === 'loading' ? <p role="status">Cargando predicciones…</p> : null}
        {findings.status === 'unavailable' ? <p role="alert">{findings.message}</p> : null}
        {findings.status === 'ready' && !findings.findings.length ? (
          <p>El análisis no registra candidatas parasitadas ni células cercanas al umbral.</p>
        ) : null}
        {findings.status === 'ready' && findings.findings.length ? (
          <table>
            <thead>
              <tr><th>Imagen</th><th>Célula</th><th>Clasificación IA</th><th>P(parasitada)</th><th>Umbral</th><th>Revisión</th><th>Acción</th></tr>
            </thead>
            <tbody>
              {findings.findings.map((finding) => (
                <tr key={finding.predictionId}>
                  <td>{finding.imageSequence}</td>
                  <td>{finding.cellCode}</td>
                  <td>
                    {finding.label === 'parasitized' ? 'Candidata parasitada' : finding.label === 'uninfected' ? 'No infectada' : '—'}
                    {finding.nearThreshold ? ' · cercana al umbral' : ''}
                  </td>
                  <td>{formatProbability(finding.probabilityParasitized)}</td>
                  <td>{formatProbability(finding.threshold)}</td>
                  <td>{reviewLabel(finding.reviewStatus)}</td>
                  <td>
                    <button type="button" className="frotis-v3-button" onClick={() => onOpenFinding(finding)}>
                      Ver en microscopio
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </section>

      <p className="frotis-v3-report-note" role="note">
        Resultado experimental: requiere revisión experta y no constituye un diagnóstico clínico.
      </p>
    </article>
  );
}
