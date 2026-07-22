import { useEffect, useState, type KeyboardEvent, type ReactNode } from 'react';

import type { Datasource } from '../types/api';

export type PageKey =
  | 'dashboard' | 'runs' | 'clinical-evaluation' | 'models' | 'model-versions'
  | 'deployments' | 'traceability' | 'run-detail' | 'explainability'
  | 'uploaded-predictions' | 'dataset-browser' | 'datasets' | 'errors';

interface LayoutProps { page: PageKey; datasource: string; datasources: Datasource[];
  onPageChange: (page: PageKey) => void; onDatasourceChange: (datasource: string) => void; children: ReactNode; }

export const modelAiNavItems: Array<{ page: PageKey; label: string }> = [
  { page: 'dashboard', label: 'Resumen' }, { page: 'runs', label: 'Entrenamientos' },
  { page: 'clinical-evaluation', label: 'Evaluaciones' }, { page: 'models', label: 'Comparación de modelos' },
  { page: 'model-versions', label: 'Modelos liberados' }, { page: 'deployments', label: 'Despliegues' },
  { page: 'traceability', label: 'Trazabilidad' }, { page: 'explainability', label: 'Explicabilidad' },
  { page: 'uploaded-predictions', label: 'Predicciones' }, { page: 'dataset-browser', label: 'Dataset' },
  { page: 'datasets', label: 'Datasets y modelos' },
];

export function Layout({ page, datasource, datasources, onPageChange, onDatasourceChange, children }: LayoutProps) {
  const childActive = modelAiNavItems.some((item) => item.page === page) || page === 'run-detail';
  const [expanded, setExpanded] = useState(() => localStorage.getItem('model-ai-menu-expanded') !== 'false');
  useEffect(() => { if (childActive) setExpanded(true); }, [childActive]);
  useEffect(() => { localStorage.setItem('model-ai-menu-expanded', String(expanded)); }, [expanded]);
  const activeLabel = modelAiNavItems.find((item) => item.page === page)?.label ?? (page === 'run-detail' ? 'Detalle de ejecución' : 'Errores y logs');
  const keyboardToggle = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'ArrowRight') setExpanded(true);
    if (event.key === 'ArrowLeft') setExpanded(false);
  };
  return <div className="app-shell">
    <aside>
      <div className="brand"><span>Capstone</span><strong>ML Dashboard</strong></div>
      <nav aria-label="Navegación principal">
        <button className={`nav-parent ${childActive ? 'active-parent' : ''}`} type="button"
          aria-expanded={expanded} aria-controls="model-ai-submenu" onClick={() => setExpanded((value) => !value)} onKeyDown={keyboardToggle}>
          <span aria-hidden="true">◈</span><span>Modelo IA</span><span className="nav-chevron" aria-hidden="true">{expanded ? '▾' : '▸'}</span>
        </button>
        {expanded ? <div id="model-ai-submenu" className="nav-submenu">
          {modelAiNavItems.map((item) => <button key={item.page} className={page === item.page ? 'active' : ''}
            aria-current={page === item.page ? 'page' : undefined} onClick={() => onPageChange(item.page)} type="button">{item.label}</button>)}
        </div> : null}
        <button className={page === 'errors' ? 'active' : ''} aria-current={page === 'errors' ? 'page' : undefined}
          onClick={() => onPageChange('errors')} type="button">Errores y logs</button>
      </nav>
    </aside>
    <main>
      <header className="topbar"><div><p>Datasource</p><select value={datasource} onChange={(event) => onDatasourceChange(event.target.value)} aria-label="Datasource">
        {datasources.map((item) => <option key={item.key} value={item.key} disabled={!item.enabled}>{item.label} - {item.domain}</option>)}
      </select></div><span className="api-note">Frontend conectado solo a backend_api</span></header>
      <div className="breadcrumb" aria-label="Migas de pan"><span>{childActive ? 'Modelo IA' : 'Administración'}</span><span aria-hidden="true">/</span><strong>{activeLabel}</strong></div>
      {children}
    </main>
  </div>;
}
