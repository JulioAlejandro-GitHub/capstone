import { History, Plus } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';

import { routes, withAllowedQuery } from '../../../router';

/** Enlaces compactos del header: nuevo análisis e Historial (sin modificar esas vistas). */
export function WorkspaceLinks({ showNewAnalysis }: { showNewAnalysis: boolean }) {
  const [searchParams] = useSearchParams();
  const datasource = searchParams.get('datasource');
  return (
    <>
      {showNewAnalysis ? (
        <Link
          className="frotis-v3-header-link"
          to={withAllowedQuery(routes.smearMicroscope, { datasource })}
          aria-label="Comenzar un nuevo análisis microscópico"
          title="Nuevo análisis"
        >
          <Plus aria-hidden="true" />
        </Link>
      ) : null}
      <Link
        className="frotis-v3-header-link"
        to={withAllowedQuery(routes.smearHistory, { datasource })}
        aria-label="Ir al historial de análisis"
        title="Historial de análisis"
      >
        <History aria-hidden="true" />
      </Link>
    </>
  );
}
