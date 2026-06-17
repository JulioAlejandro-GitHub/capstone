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

export function stringifyJson(value: JsonValue | unknown) {
  if (value === null || value === undefined) return '-';
  return JSON.stringify(value, null, 2);
}

