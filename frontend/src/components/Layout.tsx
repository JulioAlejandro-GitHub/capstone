import { useEffect, useState, type KeyboardEvent } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';

import { routes, withAllowedQuery } from '../router';
import type { Datasource } from '../types/api';

export const modelAiNavItems = [
  { path: routes.summary, label: 'Resumen' },
  { path: routes.runs, label: 'Ejecuciones' },
  { path: routes.evaluations, label: 'Evaluaciones' },
  { path: routes.comparison, label: 'Comparación de modelos' },
  { path: routes.modelVersions, label: 'Modelos liberados' },
  { path: routes.deployments, label: 'Despliegues' },
  { path: routes.traceability, label: 'Trazabilidad' },
  { path: routes.explainability, label: 'Explicabilidad' },
  { path: routes.predictions, label: 'Predicciones' },
  { path: routes.dataset, label: 'Dataset' },
  { path: routes.datasetsModels, label: 'Datasets y modelos' },
  { path: routes.errorsLogs, label: 'Errores y logs' },
] as const;

interface LayoutProps {
  datasource: string;
  datasources: Datasource[];
  onDatasourceChange: (datasource: string) => void;
}

const sectionForPath = (pathname: string) =>
  modelAiNavItems.find((item) => pathname === item.path || pathname.startsWith(`${item.path}/`));

export function Layout({ datasource, datasources, onDatasourceChange }: LayoutProps) {
  const location = useLocation();
  const childActive = location.pathname.startsWith('/modelo-ia/');
  const active = sectionForPath(location.pathname);
  const [expanded, setExpanded] = useState(() => localStorage.getItem('model-ai-menu-expanded') !== 'false');
  useEffect(() => { if (childActive) setExpanded(true); }, [childActive]);
  useEffect(() => { localStorage.setItem('model-ai-menu-expanded', String(expanded)); }, [expanded]);
  useEffect(() => {
    document.title = `${active?.label ?? 'Página no encontrada'} | ML Dashboard`;
  }, [active?.label]);
  const keyboardToggle = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'ArrowRight') setExpanded(true);
    if (event.key === 'ArrowLeft') setExpanded(false);
  };
  const query = { datasource };
  return <div className="app-shell">
    <aside>
      <div className="brand"><span>Capstone</span><strong>ML Dashboard</strong></div>
      <nav aria-label="Navegación principal">
        <button className={`nav-parent ${childActive ? 'active-parent' : ''}`} type="button"
          aria-expanded={expanded} aria-controls="model-ai-submenu" onClick={() => setExpanded((value) => !value)} onKeyDown={keyboardToggle}>
          <span aria-hidden="true">◈</span><span>Modelo IA</span><span className="nav-chevron" aria-hidden="true">{expanded ? '▾' : '▸'}</span>
        </button>
        {expanded ? <div id="model-ai-submenu" className="nav-submenu">
          {modelAiNavItems.map((item) => <NavLink key={item.path} to={withAllowedQuery(item.path, query)}
            className={({ isActive }) => isActive ? 'active' : undefined}>{item.label}</NavLink>)}
        </div> : null}
      </nav>
    </aside>
    <main>
      <header className="topbar"><div><p>Datasource</p><select value={datasource} onChange={(event) => onDatasourceChange(event.target.value)} aria-label="Datasource">
        {datasources.map((item) => <option key={item.key} value={item.key} disabled={!item.enabled}>{item.label} - {item.domain}</option>)}
      </select></div><span className="api-note">Frontend conectado solo a backend_api</span></header>
      <nav className="breadcrumb" aria-label="Migas de pan">
        <Link to={withAllowedQuery(routes.summary, query)}>Modelo IA</Link><span aria-hidden="true">/</span>
        {active ? <Link to={withAllowedQuery(active.path, query)} aria-current={location.pathname === active.path ? 'page' : undefined}>{active.label}</Link> : <strong>Página no encontrada</strong>}
        {active && location.pathname !== active.path ? <><span aria-hidden="true">/</span><strong>Detalle</strong></> : null}
      </nav>
      <Outlet />
    </main>
  </div>;
}
