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

export function formatDuration(value: number | null | undefined) {
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

export function stringifyJson(value: JsonValue | unknown) {
  if (value === null || value === undefined) return '-';
  return JSON.stringify(value, null, 2);
}
