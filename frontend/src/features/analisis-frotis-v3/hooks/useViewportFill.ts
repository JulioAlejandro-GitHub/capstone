import { useLayoutEffect, useRef, useState } from 'react';

/**
 * Mide el alto disponible bajo el header global de Capstone para que el
 * workspace ocupe el resto del viewport sin modificar el layout compartido.
 */
export function useViewportFill<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [height, setHeight] = useState<number | null>(null);

  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return undefined;
    const measure = () => {
      const top = element.getBoundingClientRect().top + window.scrollY;
      setHeight(Math.max(360, Math.round(window.innerHeight - top)));
    };
    measure();
    window.addEventListener('resize', measure);
    const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(measure) : null;
    if (element.parentElement) observer?.observe(element.parentElement);
    return () => {
      window.removeEventListener('resize', measure);
      observer?.disconnect();
    };
  }, []);

  return { ref, height };
}
