import type { CSSProperties } from 'react';

import { useAuth } from '../../auth';

// Priority used when the user holds several roles: the highest one drives the avatar.
const ROLE_PRIORITY = ['administrator', 'researcher', 'reviewer', 'operator', 'read_only'] as const;
type UserRole = (typeof ROLE_PRIORITY)[number];

const ROLE_LABELS: Record<UserRole, string> = {
  administrator: 'Administrador',
  researcher: 'Investigador',
  reviewer: 'Revisor',
  operator: 'Operador',
  read_only: 'Solo lectura',
};

const ROLE_ACCENTS: Record<UserRole, string> = {
  administrator: '#f59e0b',
  researcher: '#8b5cf6',
  reviewer: '#38bdf8',
  operator: '#48c78e',
  read_only: '#94a3b8',
};

// Stroke icons in the NavigationIcon style (24x24, currentColor).
const ROLE_ICONS: Record<UserRole, string[]> = {
  administrator: ['M12 3 5 5.8v5.4c0 4.6 3.2 7.9 7 9.3 3.8-1.4 7-4.7 7-9.3V5.8z'],
  researcher: ['M9.5 3h5', 'M10 3v5.8L4.9 18.2a2 2 0 0 0 1.8 2.8h10.6a2 2 0 0 0 1.8-2.8L14 8.8V3'],
  reviewer: ['M10.5 4.5a6 6 0 1 0 0 12 6 6 0 0 0 0-12z', 'm15 15 5 5', 'm8 10.5 1.8 1.8 3.2-3.8'],
  operator: [
    'M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z',
    'M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
  ],
  read_only: ['M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z', 'M12 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z'],
};

const FALLBACK_ICON = ['M12 4a4 4 0 1 0 0 8 4 4 0 0 0 0-8z', 'M4.5 20.5c1.5-3.5 4-5 7.5-5s6 1.5 7.5 5'];

function primaryRole(roles: string[]): UserRole | null {
  for (const role of ROLE_PRIORITY) {
    if (roles.includes(role)) return role;
  }
  return null;
}

export function UserMenu() {
  const { user } = useAuth();
  const role = user ? primaryRole(user.roles) : null;
  const roleLabel = role ? ROLE_LABELS[role] : 'Usuario';
  const accent = role ? ROLE_ACCENTS[role] : '#94a3b8';
  const description = `Cuenta de ${user?.username ?? 'usuario'} (${roleLabel})`;
  return (
    <button type="button" className="user-menu-button" data-role={role ?? 'unknown'}
      style={{ '--user-menu-accent': accent } as CSSProperties}
      aria-label={description} title={description}>
      <svg className="user-menu-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        {(role ? ROLE_ICONS[role] : FALLBACK_ICON).map((path, index) => <path key={index} d={path} />)}
      </svg>
    </button>
  );
}
