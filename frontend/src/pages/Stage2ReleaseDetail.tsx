import { Navigate, useLocation, useParams } from 'react-router-dom';

import { InvalidEntityId } from '../components/RouteState';
import { isValidPublicId, routes, withAllowedQuery } from '../router';

export function Stage2ReleaseDetail({ datasource }: { datasource: string }) {
  const { trainingRunId } = useParams();
  const location = useLocation();
  if (!isValidPublicId(trainingRunId)) {
    return <InvalidEntityId
      kind="ejecución"
      listPath={withAllowedQuery(routes.runs, { datasource })}
    />;
  }

  const search = new URLSearchParams(location.search);
  search.set('datasource', datasource);
  search.set('run', trainingRunId);
  search.set('stage2', 'publicacion');
  return <Navigate replace to={`${routes.runs}?${search.toString()}`} />;
}
