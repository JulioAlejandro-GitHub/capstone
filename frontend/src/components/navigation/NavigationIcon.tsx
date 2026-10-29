import type { NavigationIconName } from './navigationConfig';

const paths: Record<NavigationIconName | 'copy', string[]> = {
  copy: ['M9 9h11v11H9z', 'M5 15H4V4h11v1'],
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
  stethoscope: ['M11 2v2', 'M5 2v2', 'M5 3H4a2 2 0 0 0-2 2v4a6 6 0 0 0 12 0V5a2 2 0 0 0-2-2h-1', 'M8 15a6 6 0 0 0 12 0v-3', 'M20 10a2 2 0 1 1-4 0 2 2 0 0 1 4 0z'],
  microscope: ['M6 18h8', 'M3 22h18', 'M14 22a7 7 0 1 0 0-14h-1', 'M9 14h2', 'M9 12a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2Z', 'M12 6V3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3'],
  percent: ['M19 5L5 19', 'M6.5 6.5', 'M17.5 17.5'],
  boxes: ['M2.97 12.92A2 2 0 0 0 2 14.63v3.24a2 2 0 0 0 .97 1.71l3 1.8a2 2 0 0 0 2.06 0L12 19v-5.5l-5-3-4.03 2.42Z'],
  }

export function NavigationIcon({ name }: { name: NavigationIconName | 'copy' }) {
  return <svg className="navigation-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {paths[name].map((path, index) => <path key={index} d={path} />)}
  </svg>;
}
