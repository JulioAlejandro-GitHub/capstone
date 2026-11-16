import { useEffect, useState } from 'react';

import { api } from '../../../services/api';

/** Recorte persistido de una célula (contenido autenticado, sin modificar). */
export function useCellCrop(cropId: string | null, contentUrl: string | null) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    setUrl(null);
    setFailed(false);
    if (!cropId) return undefined;
    const controller = new AbortController();
    let objectUrl: string | null = null;
    api.getCellCropBlob(cropId, contentUrl, controller.signal)
      .then((blob) => {
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [contentUrl, cropId]);
  return { url, failed };
}
