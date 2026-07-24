import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

import { buildShareableUrl, routes } from '../router';

export function InvalidEntityId({ kind, listPath }: { kind: string; listPath: string }) {
  return <section className="page route-message" aria-labelledby="invalid-id-title">
    <h1 id="invalid-id-title" tabIndex={-1}>Identificador inválido</h1>
    <p>El identificador de {kind} no tiene un formato válido.</p>
    <Link className="button-link" to={listPath}>Volver a la lista</Link>
  </section>;
}

export function NotFound() {
  return <section className="page route-message" aria-labelledby="not-found-title">
    <h1 id="not-found-title" tabIndex={-1}>Página no encontrada</h1>
    <p>La dirección solicitada no existe o fue modificada.</p>
    <div className="detail-actions">
      <Link className="button-link" to={routes.summary}>Volver al resumen</Link>
      <button type="button" onClick={() => history.back()}>Volver a la página anterior</button>
    </div>
  </section>;
}

export function CopyCanonicalLink({
  pathname,
  datasource,
  extra = {},
}: {
  pathname: string;
  datasource: string;
  extra?: Record<string, string | null | undefined>;
}) {
  const [message, setMessage] = useState('');
  const copy = async () => {
    const value = buildShareableUrl(pathname, { datasource, ...extra });
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(value);
      else {
        const input = document.createElement('textarea');
        input.value = value;
        input.style.position = 'fixed';
        input.style.opacity = '0';
        document.body.appendChild(input);
        input.select();
        document.execCommand('copy');
        input.remove();
      }
      setMessage('Enlace copiado.');
    } catch {
      setMessage('No fue posible copiar el enlace.');
    }
  };
  return <span className="copy-link-action">
    <button type="button" onClick={copy}>Copiar enlace</button>
    <span role="status" aria-live="polite">{message}</span>
  </span>;
}

export function RouteEffects() {
  const location = useLocation();
  useEffect(() => {
    const heading = document.querySelector<HTMLElement>('main h1');
    heading?.setAttribute('tabindex', '-1');
    heading?.focus({ preventScroll: true });
  }, [location.pathname]);
  return null;
}
