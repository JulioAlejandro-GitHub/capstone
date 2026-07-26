import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { authApi, setAccessToken } from './services/api';

export type AuthUser = { id: string; username: string; roles: string[]; permissions: string[] };
type AuthContextValue = {
  user: AuthUser | null; loading: boolean;
  login: (username: string, password: string) => Promise<void>; logout: () => void;
};
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    authApi.me().then(setUser).catch(() => setAccessToken(null)).finally(() => setLoading(false));
  }, []);
  const value = useMemo(() => ({
    user, loading,
    async login(username: string, password: string) {
      const result = await authApi.login(username, password);
      setAccessToken(result.access_token);
      setUser(await authApi.me());
    },
    logout() { setAccessToken(null); setUser(null); },
  }), [user, loading]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth requiere AuthProvider');
  return value;
}

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <p>Cargando sesión…</p>;
  return user ? children : <Navigate to="/login" replace state={{ from: location.pathname }} />;
}
