import { routes } from '../../router';

export type NavigationIconName =
  | 'dashboard' | 'activity' | 'evaluation' | 'compare' | 'package' | 'rocket'
  | 'trace' | 'explain' | 'prediction' | 'database' | 'datasets' | 'logs';

export type NavigationGroup = {
  id: string;
  label: string;
  items: Array<{
    id: string;
    label: string;
    path: string;
    icon: NavigationIconName;
  }>;
};

export type NavigationModule = {
  id: string;
  label: string;
  pathPrefix: string;
  mark?: string;
  icon?: NavigationIconName;
  groups: NavigationGroup[];
};

const modelAiGroups: NavigationGroup[] = [
  {
    id: 'general', label: 'General', items: [
      { id: 'summary', label: 'Resumen', path: routes.summary, icon: 'dashboard' },
    ]
  },
  {
    id: 'experimentation', label: 'Experimentación', items: [
      { id: 'runs', label: 'Ejecuciones', path: routes.runs, icon: 'activity' },
    ]
  },
  {
    id: 'data', label: 'Datos', items: [
      { id: 'dataset', label: 'Dataset', path: routes.dataset, icon: 'database' },
      { id: 'datasets-models', label: 'Datasets y modelos', path: routes.datasetsModels, icon: 'datasets' },
    ]
  },
];

export const navigationModules: NavigationModule[] = [
  {
    id: 'smear-analysis',
    label: 'Análisis de frotis',
    pathPrefix: '/frotis',
    icon: 'prediction',
    groups: [{
      id: 'smear-operation',
      label: 'Operación',
      items: [
        { id: 'smear-workflow', label: 'Analizar imagen', path: routes.smearWorkflow, icon: 'prediction' },
        { id: 'smear-history', label: 'Historial de análisis', path: routes.smearHistory, icon: 'activity' },
      ],
    }],
  },
  {
    id: 'model-ai',
    label: 'Modelo IA',
    pathPrefix: '/modelo-ia',
    mark: 'AI',
    groups: modelAiGroups,
  },
];

export const navigationItems = navigationModules.flatMap((module) =>
  module.groups.flatMap((group) => group.items));

export const pathMatches = (pathname: string, path: string) =>
  pathname === path || pathname.startsWith(`${path}/`);

export const moduleForPath = (pathname: string) =>
  navigationModules.find((module) => pathMatches(pathname, module.pathPrefix));

export const sectionForPath = (pathname: string) =>
  navigationItems.find((item) => pathMatches(pathname, item.path));
