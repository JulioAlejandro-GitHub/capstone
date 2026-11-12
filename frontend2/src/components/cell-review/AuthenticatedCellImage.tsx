import {
  createContext,
  memo,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';

import { api } from '../../services/api';
import type { CellCropSummary } from '../../types/cellReview';

const CROP_BLOB_CACHE_LIMIT = 80;

type InFlightCropBlobRequest = {
  controller: AbortController;
  promise: Promise<Blob>;
  consumers: number;
};

type CropBlobStore = {
  blobs: Map<string, Blob>;
  requests: Map<string, InFlightCropBlobRequest>;
};

const CropBlobStoreContext = createContext<CropBlobStore | null>(null);

export function AuthenticatedImageCacheProvider({ children }: { children: ReactNode }) {
  const storeRef = useRef<CropBlobStore | null>(null);
  if (!storeRef.current) {
    storeRef.current = { blobs: new Map(), requests: new Map() };
  }

  useEffect(() => {
    const store = storeRef.current;
    return () => {
      store?.requests.forEach((request) => request.controller.abort());
      store?.requests.clear();
      store?.blobs.clear();
    };
  }, []);

  return (
    <CropBlobStoreContext.Provider value={storeRef.current}>
      {children}
    </CropBlobStoreContext.Provider>
  );
}

function rememberCropBlob(store: CropBlobStore, cropId: string, blob: Blob) {
  store.blobs.delete(cropId);
  store.blobs.set(cropId, blob);

  while (store.blobs.size > CROP_BLOB_CACHE_LIMIT) {
    const oldestCropId = store.blobs.keys().next().value;
    if (oldestCropId === undefined) break;
    store.blobs.delete(oldestCropId);
  }
}

function readCachedCropBlob(store: CropBlobStore, cropId: string) {
  const blob = store.blobs.get(cropId);
  if (!blob) return null;

  // Refresh insertion order so the bounded map behaves as a small LRU cache.
  store.blobs.delete(cropId);
  store.blobs.set(cropId, blob);
  return blob;
}

function createCropBlobRequest(
  store: CropBlobStore,
  crop: CellCropSummary,
): InFlightCropBlobRequest {
  const controller = new AbortController();
  let request: InFlightCropBlobRequest;
  const promise = api
    .getCellCropBlob(crop.id, crop.content_url, controller.signal)
    .then((blob) => {
      rememberCropBlob(store, crop.id, blob);
      return blob;
    })
    .finally(() => {
      if (store.requests.get(crop.id) === request) {
        store.requests.delete(crop.id);
      }
    });

  request = { controller, promise, consumers: 0 };
  store.requests.set(crop.id, request);
  return request;
}

function loadCachedCropBlob(
  store: CropBlobStore,
  crop: CellCropSummary,
  signal: AbortSignal,
): Promise<Blob> {
  if (signal.aborted) {
    return Promise.reject(new DOMException('Crop request aborted', 'AbortError'));
  }

  const cachedBlob = readCachedCropBlob(store, crop.id);
  if (cachedBlob) return Promise.resolve(cachedBlob);

  const request = store.requests.get(crop.id) ?? createCropBlobRequest(store, crop);
  request.consumers += 1;

  return new Promise<Blob>((resolve, reject) => {
    let finished = false;

    const release = () => {
      request.consumers -= 1;
      if (request.consumers === 0 && store.requests.get(crop.id) === request) {
        store.requests.delete(crop.id);
        request.controller.abort();
      }
    };
    const finish = (callback: () => void) => {
      if (finished) return;
      finished = true;
      signal.removeEventListener('abort', onAbort);
      release();
      callback();
    };
    const onAbort = () => {
      finish(() => reject(new DOMException('Crop request aborted', 'AbortError')));
    };

    request.promise.then(
      (blob) => finish(() => resolve(blob)),
      (error: unknown) => finish(() => reject(error)),
    );
    signal.addEventListener('abort', onAbort, { once: true });
    if (signal.aborted) onAbort();
  });
}

export type ObjectUrlState = {
  url: string | null;
  loading: boolean;
  error: boolean;
};

type ObjectUrlInternalState = ObjectUrlState & {
  resourceKey: string | null | undefined;
};

export function useAuthenticatedObjectUrl(
  load: (signal: AbortSignal) => Promise<Blob>,
  enabled = true,
  resourceKey?: string | null,
): ObjectUrlState {
  const [state, setState] = useState<ObjectUrlInternalState>({
    url: null,
    loading: enabled,
    error: false,
    resourceKey,
  });

  useEffect(() => {
    if (!enabled) {
      setState({ url: null, loading: false, error: false, resourceKey });
      return;
    }
    const controller = new AbortController();
    let active = true;
    let objectUrl: string | null = null;
    setState({ url: null, loading: true, error: false, resourceKey });
    load(controller.signal)
      .then((blob) => {
        const nextUrl = URL.createObjectURL(blob);
        if (!active) {
          URL.revokeObjectURL(nextUrl);
          return;
        }
        objectUrl = nextUrl;
        setState({ url: nextUrl, loading: false, error: false, resourceKey });
      })
      .catch(() => {
        if (active) setState({ url: null, loading: false, error: true, resourceKey });
      });
    return () => {
      active = false;
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [enabled, load, resourceKey]);

  if (!enabled || state.resourceKey !== resourceKey) {
    return { url: null, loading: enabled, error: false };
  }
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
  const cropStore = useContext(CropBlobStoreContext);
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
      return cropStore
        ? loadCachedCropBlob(cropStore, crop, signal)
        : api.getCellCropBlob(crop.id, crop.content_url, signal);
    },
    [crop, cropStore],
  );
  const { url, loading, error } = useAuthenticatedObjectUrl(
    load,
    visible && Boolean(crop),
    crop?.id,
  );

  return (
    <div ref={hostRef} className="cell-crop-image">
      {url ? <img src={url} alt={alt} loading="lazy" decoding="async" draggable={false} /> : null}
      {!crop ? <span>Crop no disponible</span> : null}
      {crop && loading ? <span aria-label="Cargando crop">Cargando…</span> : null}
      {crop && error ? <span role="img" aria-label="Crop no disponible">Crop no disponible</span> : null}
    </div>
  );
});
