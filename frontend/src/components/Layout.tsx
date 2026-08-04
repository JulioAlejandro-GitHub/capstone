import { useEffect, useRef, useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';

import { routes, withAllowedQuery } from '../router';
import type { Datasource } from '../types/api';
import { AppSidebar } from './navigation/AppSidebar';
import { moduleForPath, sectionForPath } from './navigation/navigationConfig';

interface LayoutProps {
  datasource: string;
  datasources: Datasource[];
  onDatasourceChange: (datasource: string) => void;
}

export function Layout({ datasource, datasources, onDatasourceChange }: LayoutProps) {
  const location = useLocation();
  const active = sectionForPath(location.pathname);
  const activeModule = moduleForPath(location.pathname);
  const [mobileOpen, setMobileOpen] = useState(false);
  const mobileTriggerRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    document.title = `${active?.label ?? 'Página no encontrada'} | ML Dashboard`;
  }, [active?.label]);
  const query = { datasource };
  return <div className="app-shell">
    <AppSidebar datasource={datasource} mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)}
      mobileTriggerRef={mobileTriggerRef} />
    <main className="app-content">
      <header className="topbar">
        <div className="mobile-navigation">
          <button ref={mobileTriggerRef} className="mobile-menu-trigger" type="button" aria-label="Abrir navegación"
            aria-expanded={mobileOpen} aria-controls="app-sidebar" onClick={() => setMobileOpen(true)}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
          </button>
          <div><strong>ML Dashboard</strong><span>{active?.label ?? 'Navegación'}</span></div>
        </div>
        <label className="datasource-selector"><span>Datasource activo</span>
          <select value={datasource} onChange={(event) => onDatasourceChange(event.target.value)} aria-label="Datasource">
            {datasources.map((item) => <option key={item.key} value={item.key} disabled={!item.enabled}>{item.label} - {item.domain}</option>)}
          </select>
        </label>
        <div className="backend-status" title="Frontend conectado mediante backend_api">
          <span aria-hidden="true" />Backend conectado
        </div>
      </header>
      <nav className="breadcrumb" aria-label="Migas de pan">
        {activeModule?.id === 'model-ai'
          ? <Link to={withAllowedQuery(routes.summary, query)}>{activeModule.label}</Link>
          : <strong>{activeModule?.label ?? 'Navegación'}</strong>}
        <span aria-hidden="true">/</span>
        {active ? <Link to={withAllowedQuery(active.path, query)} aria-current={location.pathname === active.path ? 'page' : undefined}>{active.label}</Link> : <strong>Página no encontrada</strong>}
        {active && location.pathname !== active.path ? <><span aria-hidden="true">/</span><strong>Detalle</strong></> : null}
      </nav>
      <Outlet />
    </main>
  </div>;
}
