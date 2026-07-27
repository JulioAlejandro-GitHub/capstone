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

export const navigationGroups: NavigationGroup[] = [
  {
    id: 'general', label: 'General', items: [
      { id: 'summary', label: 'Resumen', path: routes.summary, icon: 'dashboard' },
    ]
  },
  {
    id: 'experimentation', label: 'Experimentación', items: [
      { id: 'runs', label: 'Ejecuciones', path: routes.runs, icon: 'activity' },
      // { id: 'evaluations', label: 'Evaluaciones', path: routes.evaluations, icon: 'evaluation' },
      // { id: 'comparison', label: 'Comparación de modelos', path: routes.comparison, icon: 'compare' },
      // { id: 'explainability', label: 'Explicabilidad', path: routes.explainability, icon: 'explain' },
    ]
  },
  // {
  //   id: 'governance', label: 'Gobernanza', items: [
  //     { id: 'model-versions', label: 'Modelos liberados', path: routes.modelVersions, icon: 'package' },
  //     { id: 'deployments', label: 'Despliegues', path: routes.deployments, icon: 'rocket' },
  //     { id: 'traceability', label: 'Trazabilidad', path: routes.traceability, icon: 'trace' },
  //   ]
  // },
  // {
  //   id: 'operation', label: 'Operación', items: [
  //     { id: 'predictions', label: 'Predicciones', path: routes.predictions, icon: 'prediction' },
  //     { id: 'logs', label: 'Errores y logs', path: routes.errorsLogs, icon: 'logs' },
  //   ]
  // },
  {
    id: 'data', label: 'Datos', items: [
      { id: 'smear-upload', label: 'Cargar frotis', path: routes.smearUpload, icon: 'database' },
      { id: 'dataset', label: 'Dataset', path: routes.dataset, icon: 'database' },
      { id: 'datasets-models', label: 'Datasets y modelos', path: routes.datasetsModels, icon: 'datasets' },
    ]
  },
];

export const navigationItems = navigationGroups.flatMap((group) => group.items);

export const sectionForPath = (pathname: string) =>
  navigationItems.find((item) => pathname === item.path || pathname.startsWith(`${item.path}/`));
