import { useCallback, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { isValidPublicId, routes, withAllowedQuery } from '../../router';
import { ExistingAnalysisSession } from './components/ExistingAnalysisSession';
import { LiveAnalysisSession } from './components/LiveAnalysisSession';
import { MicroscopeWorkspace } from './components/MicroscopeWorkspace';
import { WorkspaceLinks } from './components/WorkspaceLinks';
import { WorkspaceMessage } from './components/WorkspaceMessage';
import './styles/tokens_frotis_v3.css';
import './styles/workspace.css';

/**
 * Análisis de frotis v3 — Microscopio Digital Inmersivo.
 *
 * Entrada única para los dos accesos:
 *   A. `/frotis/microscopio`               → incorporar imágenes y comenzar un análisis.
 *   B. `/frotis/microscopio/:analysisId`   → abrir un análisis existente.
 *
 * Ambos terminan en el mismo `MicroscopeWorkspace`. Un análisis creado en esta
 * sesión conserva su workspace montado cuando la URL adquiere el `analysisId`.
 */
export function MicroscopioPage() {
  const { analysisId } = useParams();
  const routeAnalysisId = analysisId ?? null;
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const datasource = searchParams.get('datasource');

  // Análisis que pertenece a la sesión en curso. El ref se actualiza de forma
  // síncrona antes de navegar para que ningún render intermedio lo trate como
  // un análisis ajeno y desmonte la sesión.
  const liveRef = useRef<string | null>(null);
  const [liveAnalysisId, setLiveAnalysisId] = useState<string | null>(null);
  const claim = useCallback((id: string | null) => {
    liveRef.current = id;
    setLiveAnalysisId(id);
  }, []);

  // Reanudar: la sesión en curso recupera el análisis mediante el parámetro
  // `analysis` del workflow existente (solo lecturas) y ofrece la acción manual.
  const resume = useCallback((id: string) => {
    claim(id);
    navigate(
      withAllowedQuery(routes.smearMicroscopeAnalysis(id), { datasource, analysis: id }),
      { replace: true },
    );
  }, [claim, datasource, navigate]);

  if (routeAnalysisId && !isValidPublicId(routeAnalysisId)) {
    return (
      <MicroscopeWorkspace
        analysis={null}
        status={{ label: 'Identificador inválido', tone: 'blocked' }}
        headerActions={<WorkspaceLinks showNewAnalysis />}
        takeover={(
          <WorkspaceMessage
            kind="problem"
            title="Identificador inválido"
            detail="El identificador del análisis no tiene un formato válido."
          >
            <Link className="frotis-v3-button" to={withAllowedQuery(routes.smearHistory, { datasource })}>
              Volver al historial
            </Link>
          </WorkspaceMessage>
        )}
      />
    );
  }

  const isExisting = routeAnalysisId !== null
    && routeAnalysisId !== liveAnalysisId
    && routeAnalysisId !== liveRef.current;

  return isExisting
    ? <ExistingAnalysisSession key={routeAnalysisId} analysisId={routeAnalysisId} onResume={resume} />
    : <LiveAnalysisSession routeAnalysisId={routeAnalysisId} onClaim={claim} />;
}
