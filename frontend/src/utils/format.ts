import type { JsonValue } from '../types/api';

export function formatMetric(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return '-';
  return Number(value).toFixed(4);
}

export function formatDate(value: string | null | undefined) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

export function formatDuration(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value) || value < 0) {
    return '-';
  }

  const totalSeconds = Math.floor(value);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  return [hours, minutes, seconds]
    .map((part) => String(part).padStart(2, '0'))
    .join(':');
}

const RUNNING_STATUSES = new Set(['started', 'running', 'in_progress', 'in-progress']);

export function getRunDuration(
  startedAt?: string | null,
  finishedAt?: string | null,
  durationSeconds?: number | null,
  status?: string | null,
): string {
  const normalizedStatus = status?.trim().toLowerCase();
  if (!finishedAt && normalizedStatus && RUNNING_STATUSES.has(normalizedStatus)) {
    return 'En ejecución';
  }

  if (
    durationSeconds !== null
    && durationSeconds !== undefined
    && Number.isFinite(durationSeconds)
    && durationSeconds >= 0
  ) {
    return formatDuration(durationSeconds);
  }

  if (!startedAt || !finishedAt) return 'No disponible';

  const started = new Date(startedAt).getTime();
  const finished = new Date(finishedAt).getTime();
  if (!Number.isFinite(started) || !Number.isFinite(finished) || finished < started) {
    return 'No disponible';
  }

  return formatDuration((finished - started) / 1000);
}

export function stringifyJson(value: JsonValue | unknown) {
  if (value === null || value === undefined) return '-';
  return JSON.stringify(value, null, 2);
}
