import { createContext, useContext, useState, type ReactNode } from 'react';

interface Selection {
  ids: string[];
  add: (id: string, maximum: number) => void;
  remove: (id: string) => void;
}
const ComparisonContext = createContext<Selection | null>(null);

export function addComparisonRun(ids: string[], id: string, maximum: number): string[] {
  return !id || ids.includes(id) || !Number.isInteger(maximum) || ids.length >= maximum
    ? ids : [...ids, id];
}

export function ComparisonSelectionProvider({ children }: { children: ReactNode }) {
  const [ids, setIds] = useState<string[]>([]);
  return <ComparisonContext.Provider value={{ ids,
    add: (id, maximum) => setIds(current => addComparisonRun(current, id, maximum)),
    remove: id => setIds(current => current.filter(value => value !== id)),
  }}>{children}</ComparisonContext.Provider>;
}

export function useComparisonSelection() {
  const selection = useContext(ComparisonContext);
  if (!selection) throw new Error('ComparisonSelectionProvider requerido');
  return selection;
}
