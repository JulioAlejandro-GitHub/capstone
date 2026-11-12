import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError, api } from '../../services/api';
import type {
  ScientificValidationAnnotation,
  ScientificValidationAnnotationEvent,
  ScientificValidationTarget,
} from '../../types/scientificValidation';

const safeDate = (value: string) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString();
};

type Props = {
  title: string;
  sessionId: string | null;
  targetType: ScientificValidationTarget;
  targetId: string | null;
  canAnnotate: boolean;
  onCountChange?: (count: number) => void;
  targetContext?: string;
};

export function ScientificAnnotations({
  title,
  sessionId,
  targetType,
  targetId,
  canAnnotate,
  onCountChange,
  targetContext,
}: Props) {
  const [items, setItems] = useState<ScientificValidationAnnotation[]>([]);
  const [histories, setHistories] = useState<Record<string, ScientificValidationAnnotationEvent[]>>({});
  const [editingId, setEditingId] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [category, setCategory] = useState('nota');
  const [content, setContent] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const countChangeRef = useRef(onCountChange);
  useEffect(() => { countChangeRef.current = onCountChange; }, [onCountChange]);

  const load = useCallback(async () => {
    if (!targetId) {
      setItems([]);
      countChangeRef.current?.(0);
      return;
    }
    try {
      const page = await api.listScientificValidationAnnotations(sessionId, {
        target_type: targetType,
        ...(targetType === 'cell'
          ? { cell_id: targetId }
          : targetType === 'sample' ? { sample_id: targetId } : { analysis_run_id: targetId }),
      });
      setItems(page.items);
      countChangeRef.current?.(page.total);
      setError('');
    } catch {
      setError('No fue posible cargar las anotaciones científicas.');
    }
  }, [sessionId, targetId, targetType]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    setAdding(false);
    setEditingId(null);
    setCategory('nota');
    setContent('');
    setMessage('');
  }, [targetId]);

  const beginEdit = (annotation: ScientificValidationAnnotation) => {
    setEditingId(annotation.id);
    setAdding(false);
    setCategory(annotation.category);
    setContent(annotation.content);
    setError('');
  };

  const save = async () => {
    if (!targetId || !content.trim() || !category.trim()) return;
    setSaving(true);
    setError('');
    try {
      if (editingId) {
        const current = items.find((item) => item.id === editingId);
        if (!current) return;
        await api.updateScientificValidationAnnotation(sessionId, editingId, {
          category: category.trim(), content: content.trim(), version: current.version,
        });
        setMessage('Anotación actualizada.');
      } else {
        await api.createScientificValidationAnnotation(sessionId, {
          target_type: targetType,
          ...(targetType === 'cell'
            ? { cell_id: targetId }
            : targetType === 'sample' ? { sample_id: targetId } : { analysis_run_id: targetId }),
          category: category.trim(), content: content.trim(),
        });
        setMessage('Anotación agregada.');
      }
      setAdding(false);
      setEditingId(null);
      setCategory('nota');
      setContent('');
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 409
        ? 'Esta anotación fue modificada por otro usuario. Actualice la información antes de guardar.'
        : caught instanceof ApiError && caught.status === 403
          ? 'Tu rol no permite editar anotaciones científicas.'
          : 'No fue posible guardar la anotación.');
      if (caught instanceof ApiError && caught.status === 409) await load();
    } finally {
      setSaving(false);
    }
  };

  const loadHistory = async (annotationId: string) => {
    if (histories[annotationId]) return;
    try {
      const page = await api.getScientificValidationAnnotationHistory(sessionId, annotationId);
      setHistories((current) => ({ ...current, [annotationId]: page.items }));
    } catch {
      setError('No fue posible cargar el historial de la anotación.');
    }
  };

  const editable = Boolean(targetId && canAnnotate);
  return (
    <section className="scientific-annotations" aria-label={title}>
      <header>
        <div>
          <h3>{title}</h3>
          {targetContext ? <small>{targetContext}</small> : null}
        </div>
        {editable && !adding && !editingId ? (
          <button type="button" onClick={() => setAdding(true)} aria-label={`Agregar ${title.toLocaleLowerCase()}`}>
            + Agregar
          </button>
        ) : null}
      </header>
      {items.length ? (
        <ul>
          {items.map((annotation) => (
            <li key={annotation.id}>
              <div><strong>{annotation.category}</strong><span>{annotation.content}</span></div>
              <small>
                {annotation.updated_by_username ?? annotation.created_by_username ?? annotation.updated_by}
                {' · '}{safeDate(annotation.created_at)}
                {annotation.updated_at !== annotation.created_at ? ` · Modificada ${safeDate(annotation.updated_at)}` : ''}
              </small>
              <div className="scientific-annotation-actions">
                {editable ? <button type="button" onClick={() => beginEdit(annotation)}>Editar</button> : null}
                <details onToggle={(event) => {
                  if (event.currentTarget.open) void loadHistory(annotation.id);
                }}>
                  <summary>Historial</summary>
                  <ol>
                    {(histories[annotation.id] ?? []).map((event) => (
                      <li key={event.id}>
                        {event.event_type} · {event.actor_username ?? event.actor_user_id} · {safeDate(event.created_at)}
                      </li>
                    ))}
                  </ol>
                </details>
              </div>
            </li>
          ))}
        </ul>
      ) : targetId ? <p>Sin anotaciones.</p> : null}
      {(adding || editingId) && editable ? (
        <div className="cell-review-form scientific-annotation-form">
          <label>Categoría<input value={category} maxLength={120} onChange={(event) => setCategory(event.target.value)} /></label>
          <label>Nota<textarea value={content} maxLength={10000} onChange={(event) => setContent(event.target.value)} /></label>
          <div className="cell-review-actions scientific-annotation-actions">
            <button type="button" disabled={saving || !content.trim() || !category.trim()} onClick={() => void save()}>
              {editingId ? 'Guardar cambios' : 'Guardar'}
            </button>
            <button type="button" disabled={saving} onClick={() => { setAdding(false); setEditingId(null); }}>Cancelar</button>
          </div>
        </div>
      ) : null}
      {error ? <p className="cell-error" role="alert">{error}</p> : null}
      <p className="cell-review-live" aria-live="polite">{message}</p>
    </section>
  );
}
