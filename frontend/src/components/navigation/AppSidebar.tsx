import { useEffect, useRef, useState, type KeyboardEvent, type RefObject } from 'react';
import { NavLink, useLocation } from 'react-router-dom';

import { withAllowedQuery } from '../../router';
import { NavigationIcon } from './NavigationIcon';
import { navigationGroups } from './navigationConfig';

const COLLAPSED_KEY = 'ml-dashboard.sidebar.collapsed';

function readCollapsedPreference() {
  try { return localStorage.getItem(COLLAPSED_KEY) === 'true'; } catch { return false; }
}

interface Props {
  datasource: string;
  mobileOpen: boolean;
  onMobileClose: () => void;
  mobileTriggerRef: RefObject<HTMLButtonElement | null>;
}

export function AppSidebar({ datasource, mobileOpen, onMobileClose, mobileTriggerRef }: Props) {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(readCollapsedPreference);
  const [submenuOpen, setSubmenuOpen] = useState(true);
  const asideRef = useRef<HTMLElement>(null);
  const routeInside = location.pathname.startsWith('/modelo-ia/');

  useEffect(() => { if (routeInside) setSubmenuOpen(true); }, [routeInside]);
  useEffect(() => { try { localStorage.setItem(COLLAPSED_KEY, String(collapsed)); } catch { /* storage is optional */ } }, [collapsed]);
  useEffect(() => { if (mobileOpen) onMobileClose(); }, [location.pathname]);
  useEffect(() => {
    if (!mobileOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const focusable = asideRef.current?.querySelector<HTMLElement>('button, a, select');
    focusable?.focus();
    return () => { document.body.style.overflow = previousOverflow; };
  }, [mobileOpen]);

  const closeMobile = () => {
    onMobileClose();
    window.setTimeout(() => mobileTriggerRef.current?.focus(), 0);
  };
  const onKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === 'Escape' && mobileOpen) { event.preventDefault(); closeMobile(); return; }
    if (event.key !== 'Tab' || !mobileOpen) return;
    const focusable = [...(asideRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], select') ?? [])];
    if (!focusable.length) return;
    const first = focusable[0]; const last = focusable.at(-1)!;
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  };

  return <>
    <button className={`sidebar-overlay ${mobileOpen ? 'is-visible' : ''}`} type="button"
      aria-label="Cerrar navegación" tabIndex={mobileOpen ? 0 : -1} onClick={closeMobile} />
    <aside id="app-sidebar" ref={asideRef} className={`app-sidebar ${collapsed ? 'is-collapsed' : ''} ${mobileOpen ? 'is-mobile-open' : ''}`}
      aria-label="Navegación principal" onKeyDown={onKeyDown}>
      <div className="sidebar-header">
        <div className="sidebar-mark" aria-hidden="true">ML</div>
        <div className="sidebar-identity"><span>Capstone</span><strong>ML Dashboard</strong></div>
        <button className="sidebar-mobile-close" type="button" aria-label="Cerrar navegación" onClick={closeMobile}>×</button>
      </div>
      <nav className="sidebar-nav" aria-label="Módulos">
        <button className={`sidebar-parent ${routeInside ? 'contains-active' : ''}`} type="button"
          aria-expanded={submenuOpen} aria-controls="model-ai-submenu"
          onClick={() => setSubmenuOpen((value) => !value)}
          onKeyDown={(event) => {
            if (event.key === 'ArrowRight') setSubmenuOpen(true);
            if (event.key === 'ArrowLeft') setSubmenuOpen(false);
          }}>
          <span className="sidebar-parent-mark" aria-hidden="true">AI</span>
          <span className="sidebar-label">Modelo IA</span>
          <svg className="sidebar-chevron" viewBox="0 0 20 20" aria-hidden="true"><path d="m6 8 4 4 4-4" /></svg>
        </button>
        {submenuOpen ? <div id="model-ai-submenu" className="sidebar-submenu">
          {navigationGroups.map((group) => <section className="sidebar-group" key={group.id} aria-labelledby={`nav-group-${group.id}`}>
            <h2 id={`nav-group-${group.id}`}>{group.label}</h2>
            {group.items.map((item) => <NavLink key={item.id} to={withAllowedQuery(item.path, { datasource })}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              data-tooltip={collapsed ? item.label : undefined} aria-label={collapsed ? item.label : undefined}>
              <NavigationIcon name={item.icon} /><span className="sidebar-label">{item.label}</span>
            </NavLink>)}
          </section>)}
        </div> : null}
      </nav>
      <footer className="sidebar-footer">
        <span className="connection-dot" aria-hidden="true" /><span className="sidebar-label">Backend conectado</span>
      </footer>
      <button className="sidebar-collapse" type="button" aria-label={collapsed ? 'Expandir navegación' : 'Contraer navegación'}
        title={collapsed ? 'Expandir navegación' : 'Contraer navegación'} onClick={() => setCollapsed((value) => !value)}>
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d={collapsed ? 'm8 5 5 5-5 5' : 'm12 5-5 5 5 5'} /></svg>
        <span className="sidebar-label">{collapsed ? 'Expandir' : 'Contraer navegación'}</span>
      </button>
    </aside>
  </>;
}
