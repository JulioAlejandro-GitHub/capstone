import { useCallback } from 'react';
import { api } from '../../services/api';
import { useAuthenticatedObjectUrl } from '../cell-review/AuthenticatedCellImage';

/** Compatibility for existing registered media that has no artifact UUID. */
export function LegacyArtifactMedia({url, label, image = false}: {url: string; label: string; image?: boolean}) {
  const load = useCallback((signal: AbortSignal) => api.getLegacyArtifactBlob(url, signal), [url]);
  const content = useAuthenticatedObjectUrl(load, true, url);
  if (content.loading) return <span role="status">Cargando artefacto…</span>;
  if (content.error || !content.url) return <span role="alert">Artefacto no disponible.</span>;
  return <a href={content.url} target="_blank" rel="noreferrer">{image ? <img src={content.url} alt={label} loading="lazy" /> : label}</a>;
}
