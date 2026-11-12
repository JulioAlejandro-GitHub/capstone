// Page-owned memory only. No persistence or reuse across authorization contexts.
export function createComparisonCache() {
  const entries = new Map<string, Promise<unknown>>();
  return {
    read<T>(key: string, load: () => Promise<T>): Promise<T> {
      const existing = entries.get(key);
      if (existing) return existing as Promise<T>;
      const pending = Promise.resolve().then(load);
      entries.set(key, pending);
      void pending.catch(() => { if (entries.get(key) === pending) entries.delete(key); });
      return pending;
    },
    clear() { entries.clear(); },
  };
}
export type ComparisonCache = ReturnType<typeof createComparisonCache>;
