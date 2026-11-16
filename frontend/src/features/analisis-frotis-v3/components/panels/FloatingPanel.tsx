import { X } from 'lucide-react';
import { useLayoutEffect, useRef, type ReactNode } from 'react';

import type { FloatingPlacement } from '../../state/floatingLayout';

/**
 * Instrumento flotante. Informa su alto natural al Layout Manager y se ubica
 * en la posición segura que este le asigna; nunca decide su propia posición.
 */
export function FloatingPanel({
  id,
  title,
  placement,
  onMeasure,
  onClose,
  children,
}: {
  id: string;
  title?: string;
  placement: FloatingPlacement | undefined;
  onMeasure: (id: string, height: number) => void;
  onClose?: () => void;
  children: ReactNode;
}) {
  const content = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const element = content.current;
    if (!element) return undefined;
    const measure = () => onMeasure(id, Math.ceil(element.scrollHeight) + 2);
    measure();
    if (typeof ResizeObserver !== 'function') return undefined;
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [id, onMeasure]);

  return (
    <section
      className="frotis-v3-floating"
      data-panel={id}
      data-mode={placement?.mode ?? 'floating'}
      aria-label={title}
      style={placement ? {
        left: placement.x,
        top: placement.y,
        width: placement.width,
        maxHeight: placement.maxHeight,
      } : { visibility: 'hidden' }}
    >
      <div ref={content} className="frotis-v3-floating-content">
        {title ? (
          <header className="frotis-v3-floating-head">
            <h2>{title}</h2>
            {onClose ? (
              <button type="button" className="frotis-v3-icon-button" onClick={onClose} aria-label={`Ocultar ${title}`}>
                <X aria-hidden="true" />
              </button>
            ) : null}
          </header>
        ) : null}
        {children}
      </div>
    </section>
  );
}
