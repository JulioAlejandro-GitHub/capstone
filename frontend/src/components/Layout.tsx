import type { ReactNode } from 'react';

import type { Datasource } from '../types/api';

export type PageKey =
  | 'dashboard'
  | 'runs'
  | 'models'
  | 'run-detail'
  | 'explainability'
  | 'datasets'
  | 'errors';

interface LayoutProps {
  page: PageKey;
  datasource: string;
  datasources: Datasource[];
  onPageChange: (page: PageKey) => void;
  onDatasourceChange: (datasource: string) => void;
  children: ReactNode;
}

const navItems: Array<{ page: PageKey; label: string }> = [
  { page: 'dashboard', label: 'Dashboard' },
  { page: 'runs', label: 'Ejecuciones' },
  { page: 'models', label: 'Comparacion modelos' },
  { page: 'explainability', label: 'Explicabilidad' },
  { page: 'datasets', label: 'Datasets y modelos' },
  { page: 'errors', label: 'Errores y logs' },
];

export function Layout({
  page,
  datasource,
  datasources,
  onPageChange,
  onDatasourceChange,
  children,
}: LayoutProps) {
  return (
    <div className="app-shell">
      <aside>
        <div className="brand">
          <span>Capstone</span>
          <strong>ML Dashboard</strong>
        </div>
        <nav>
          {navItems.map((item) => (
            <button
              key={item.page}
              className={page === item.page ? 'active' : ''}
              onClick={() => onPageChange(item.page)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <p>Datasource</p>
            <select value={datasource} onChange={(event) => onDatasourceChange(event.target.value)}>
              {datasources.map((item) => (
                <option key={item.key} value={item.key} disabled={!item.enabled}>
                  {item.label} - {item.domain}
                </option>
              ))}
            </select>
          </div>
          <span className="api-note">Frontend conectado solo a backend_api</span>
        </header>
        {children}
      </main>
    </div>
  );
}
