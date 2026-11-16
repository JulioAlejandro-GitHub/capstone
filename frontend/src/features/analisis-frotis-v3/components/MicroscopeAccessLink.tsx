import { Microscope } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

import { isValidPublicId, routes, withAllowedQuery } from '../../../router';
import '../styles/history-access.css';

const ACTION_LABEL = 'Abrir análisis en Microscopio Digital';
const TOOLTIP = 'Abrir en Microscopio Digital';

/**
 * Acceso B — Historial → Microscopio Digital.
 * Botón compacto que acompaña a «Ver detalle» sin sustituirlo. Navega con el
 * identificador real de la fila y solo arrastra `datasource`: no altera
 * filtros ni selección del historial.
 */
export function MicroscopeAccessLink({ analysisId }: { analysisId: string | null | undefined }) {
  const location = useLocation();
  if (!isValidPublicId(analysisId)) {
    return (
      <span
        className="frotis-v3-history-access is-disabled"
        role="link"
        aria-disabled="true"
        aria-label={`${ACTION_LABEL} (no disponible: el análisis no tiene un identificador válido)`}
        title="Microscopio Digital no disponible para este análisis"
      >
        <Microscope aria-hidden="true" />
      </span>
    );
  }
  const datasource = new URLSearchParams(location.search).get('datasource');
  return (
    <Link
      className="frotis-v3-history-access"
      to={withAllowedQuery(routes.smearMicroscopeAnalysis(analysisId), { datasource })}
      aria-label={ACTION_LABEL}
      title={TOOLTIP}
    >
      <Microscope aria-hidden="true" />
    </Link>
  );
}
