import { FormEvent, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { SessionStatus, useAuth } from '../auth';
import { ApiError } from '../services/api';

export function Login() {
  const { login, user, status } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const requestedPath = (location.state as { from?: string } | null)?.from ?? '/';
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await login(String(form.get('username')), String(form.get('password')));
      navigate(requestedPath, { replace: true });
    } catch (reason) {
      setError(
        reason instanceof ApiError && reason.status === 401
          ? 'Usuario o contraseña incorrectos.'
          : reason instanceof ApiError && (reason.kind === 'network' || reason.kind === 'timeout')
            ? 'No fue posible conectar con el servidor. Intenta nuevamente.'
            : 'No fue posible iniciar sesión. Intenta nuevamente.',
      );
    }
  }
  if (status === 'initializing') return <SessionStatus message="Validando sesión…" />;
  if (user) return <Navigate to={requestedPath} replace />;
  return (
    <main className="login-page">
      <section className="login-shell" aria-labelledby="login-title">
        <header className="login-heading">
          <div className="login-brand" aria-label="Capstone IA">
            <span className="login-brand-mark" aria-hidden="true">CI</span>
            <span>Capstone IA</span>
          </div>
          {/* <h1 id="login-title">Ingreso académico</h1> */}
          {/* <p>
            Plataforma de análisis de frotis sanguíneo asistido por inteligencia artificial
          </p> */}
        </header>

        <form className="login-card" onSubmit={submit}>
          <div className="login-field">
            <label htmlFor="login-username">Usuario</label>
            <input
              id="login-username"
              name="username"
              autoComplete="username"
              aria-invalid={Boolean(error)}
              aria-describedby={error ? 'login-error' : undefined}
              required
            />
          </div>

          <div className="login-field">
            <label htmlFor="login-password">Contraseña</label>
            <input
              id="login-password"
              name="password"
              type="password"
              autoComplete="current-password"
              aria-invalid={Boolean(error)}
              aria-describedby={error ? 'login-error' : undefined}
              required
            />
          </div>

          {error && <p id="login-error" className="login-error" role="alert">{error}</p>}
          <button className="login-submit" type="submit">Ingresar</button>
        </form>

        <p className="login-restriction">
          Plataforma de análisis de frotis sanguíneo asistido por inteligencia artificial
        </p>
      </section>
    </main>
  );
}
