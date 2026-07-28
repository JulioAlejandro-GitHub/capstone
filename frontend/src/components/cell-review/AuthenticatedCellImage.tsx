import { memo, useCallback, useEffect, useRef, useState } from 'react';

import { api } from '../../services/api';
import type { CellCropSummary } from '../../types/cellReview';

export type ObjectUrlState = {
  url: string | null;
  loading: boolean;
  error: boolean;
};

export function useAuthenticatedObjectUrl(
  load: (signal: AbortSignal) => Promise<Blob>,
  enabled = true,
): ObjectUrlState {
  const [state, setState] = useState<ObjectUrlState>({
    url: null,
    loading: enabled,
    error: false,
  });

  useEffect(() => {
    if (!enabled) {
      setState({ url: null, loading: false, error: false });
      return;
    }
    const controller = new AbortController();
    let active = true;
    let objectUrl: string | null = null;
    setState({ url: null, loading: true, error: false });
    load(controller.signal)
      .then((blob) => {
        const nextUrl = URL.createObjectURL(blob);
        if (!active) {
          URL.revokeObjectURL(nextUrl);
          return;
        }
        objectUrl = nextUrl;
        setState({ url: nextUrl, loading: false, error: false });
      })
      .catch(() => {
        if (active) setState({ url: null, loading: false, error: true });
      });
    return () => {
      active = false;
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [enabled, load]);

  return state;
}

type AuthenticatedCropImageProps = {
  crop: CellCropSummary | null;
  alt: string;
  eager?: boolean;
};

export const AuthenticatedCropImage = memo(function AuthenticatedCropImage({
  crop,
  alt,
  eager = false,
}: AuthenticatedCropImageProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(eager);

  useEffect(() => {
    if (eager) {
      setVisible(true);
      return;
    }
    const host = hostRef.current;
    if (!host) return;
    if (!('IntersectionObserver' in window)) {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: '180px' },
    );
    observer.observe(host);
    return () => observer.disconnect();
  }, [eager]);

  const load = useCallback(
    (signal: AbortSignal) => {
      if (!crop) return Promise.reject(new Error('Crop no disponible'));
      return api.getCellCropBlob(crop.id, crop.content_url, signal);
    },
    [crop],
  );
  const { url, loading, error } = useAuthenticatedObjectUrl(load, visible && Boolean(crop));

  return (
    <div ref={hostRef} className="cell-crop-image">
      {url ? <img src={url} alt={alt} loading="lazy" decoding="async" draggable={false} /> : null}
      {!crop ? <span>Crop no disponible</span> : null}
      {crop && loading ? <span aria-label="Cargando crop">Cargando…</span> : null}
      {crop && error ? <span role="img" aria-label="Crop no disponible">Crop no disponible</span> : null}
    </div>
  );
});
