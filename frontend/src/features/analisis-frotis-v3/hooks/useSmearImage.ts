import { useEffect, useState } from 'react';

import { ApiError, api } from '../../../services/api';

export type SmearImageState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; url: string; origin: 'local' | 'persisted' }
  | { status: 'unavailable'; message: string };

/**
 * Entrega la imagen real del frotis: la vista previa local mientras el archivo
 * recién incorporado se procesa, o el contenido autenticado persistido.
 * No transforma ni recodifica la imagen original.
 */
export function useSmearImage(imageId: string | null, localUrl: string | null): SmearImageState {
  const [persisted, setPersisted] = useState<SmearImageState>({ status: 'idle' });

  useEffect(() => {
    if (localUrl || !imageId) {
      setPersisted({ status: 'idle' });
      return undefined;
    }
    let active = true;
    let objectUrl: string | null = null;
    setPersisted({ status: 'loading' });
    api.getMicroscopyImageBlob(imageId)
      .then((url) => {
        if (!active) {
          URL.revokeObjectURL(url);
          return;
        }
        objectUrl = url;
        setPersisted({ status: 'ready', url, origin: 'persisted' });
      })
      .catch((error) => {
        if (!active) return;
        setPersisted({
          status: 'unavailable',
          message: error instanceof ApiError && error.status === 403
            ? 'Tu rol no autoriza la lectura del contenido de la imagen (scientific.images.read).'
            : 'El contenido de la imagen no está disponible.',
        });
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [imageId, localUrl]);

  if (localUrl) return { status: 'ready', url: localUrl, origin: 'local' };
  return persisted;
}
