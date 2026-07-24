import type { NavigationIconName } from './navigationConfig';

const paths: Record<NavigationIconName, string[]> = {
  dashboard: ['M4 4h6v6H4z', 'M14 4h6v4h-6z', 'M14 12h6v8h-6z', 'M4 14h6v6H4z'],
  activity: ['M4 12h3l2-6 4 12 2-6h5'],
  evaluation: ['M5 4h14v16H5z', 'm8 9 2 2 4-5', 'M8 8h2', 'M8 16h7'],
  compare: ['M7 4v16', 'm3-13-3-3-3 3', 'M17 20V4', 'm-3 13 3 3 3-3'],
  package: ['m4 7 8-4 8 4-8 4z', 'M4 7v10l8 4 8-4V7', 'M12 11v10'],
  rocket: ['M14 5c3-2 5-2 5-2s0 2-2 5l-5 5-4-4z', 'm8 12-3 1-2 3', 'm12-8 3 3', 'M8 16c-2 0-3 1-3 3 2 0 3-1 3-3z'],
  trace: ['M6 4v12a4 4 0 0 0 4 4h8', 'M6 8h7a4 4 0 0 1 4 4v1', 'M3 4h6', 'm15 6 3 3-3 3'],
  explain: ['M3 12s3-6 9-6 9 6 9 6-3 6-9 6-9-6-9-6z', 'M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z'],
  prediction: ['M4 18V9', 'M10 18V5', 'M16 18v-7', 'M22 18H2'],
  database: ['M4 6c0-2 4-3 8-3s8 1 8 3-4 3-8 3-8-1-8-3z', 'M4 6v6c0 2 4 3 8 3s8-1 8-3V6', 'M4 12v6c0 2 4 3 8 3s8-1 8-3v-6'],
  datasets: ['M3 5h8v6H3z', 'M13 5h8v6h-8z', 'M3 13h8v6H3z', 'M13 13h8v6h-8z'],
  logs: ['M5 4h14v16H5z', 'M9 8h6', 'M9 12h6', 'M9 16h3'],
};

export function NavigationIcon({ name }: { name: NavigationIconName }) {
  return <svg className="navigation-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {paths[name].map((path, index) => <path key={index} d={path} />)}
  </svg>;
}
