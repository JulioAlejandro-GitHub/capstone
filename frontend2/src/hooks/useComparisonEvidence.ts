import { useEffect, useState } from 'react';
import type { ComparisonCache } from '../utils/comparisonCache';

export function useComparisonEvidence<T>(cache: ComparisonCache, key: string | null, load: () => Promise<T>, enabled = true) {
  const [result, setResult] = useState<{ key: string; data?: T; error?: unknown } | null>(null);
  useEffect(() => {
    if (!key || !enabled) return;
    let active = true;
    cache.read(key, load).then(data => { if (active) setResult({ key, data }); },
      error => { if (active) setResult({ key, error }); });
    return () => { active = false; };
    // The key contains every effective input. Closures are deliberately not cache identities.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cache, key, enabled]);
  return { data: result?.key === key ? result?.data : undefined,
    error: result?.key === key ? result?.error : undefined,
    loading: Boolean(enabled && key && result?.key !== key) };
}
