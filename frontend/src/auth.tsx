import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import {
  ApiError,
  authApi,
  cancelPendingRequests,
  onAuthenticationFailure,
  restoreAccessToken,
  setAccessToken,
} from './services/api';

export type AuthUser = { id: string; username: string; roles: string[]; permissions: string[] };
export type AuthStatus = 'initializing' | 'authenticated' | 'unauthenticated' | 'unavailable';
type AuthContextValue = {
  user: AuthUser | null;
  status: AuthStatus;
  loading: boolean;
  retrySession: () => void;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>('initializing');
  const [restoreAttempt, setRestoreAttempt] = useState(0);

  useEffect(() => {
    onAuthenticationFailure(() => {
      setUser(null);
      setStatus('unauthenticated');
    });
    return () => onAuthenticationFailure(null);
  }, []);

  useEffect(() => {
    let active = true;
    setStatus('initializing');
    const token = restoreAccessToken();
    if (!token) {
      setUser(null);
      setStatus('unauthenticated');
      return () => { active = false; };
    }
    authApi.me()
      .then((restoredUser) => {
        if (!active) return;
        setUser(restoredUser);
        setStatus('authenticated');
      })
      .catch((error: unknown) => {
        if (!active) return;
        setUser(null);
        if (error instanceof ApiError && error.status === 401) {
          setAccessToken(null);
          setStatus('unauthenticated');
        } else {
          setStatus('unavailable');
        }
      });
    return () => { active = false; };
  }, [restoreAttempt]);

  const value = useMemo(() => ({
    user,
    status,
    loading: status === 'initializing',
    retrySession() { setRestoreAttempt((attempt) => attempt + 1); },
    async login(username: string, password: string) {
      const result = await authApi.login(username, password);
      setAccessToken(result.access_token);
      try {
        setUser(await authApi.me());
        setStatus('authenticated');
      } catch (error) {
        setAccessToken(null);
        setUser(null);
        setStatus('unauthenticated');
        throw error;
      }
    },
    logout() {
      setAccessToken(null);
      setUser(null);
      setStatus('unauthenticated');
      cancelPendingRequests();
    },
  }), [user, status]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth requiere AuthProvider');
  return value;
}

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, status, retrySession } = useAuth();
  const location = useLocation();
  if (status === 'initializing') return <SessionStatus message="Validando sesión…" />;
  if (status === 'unavailable') {
    return <SessionStatus message="No fue posible validar la sesión." onRetry={retrySession} />;
  }
  return user && status === 'authenticated'
    ? children
    : <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}${location.hash}` }} />;
}

export function SessionStatus({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <main aria-live="polite" className="route-state">
      <p>{message}</p>
      {onRetry && <button type="button" onClick={onRetry}>Reintentar</button>}
    </main>
  );
}
