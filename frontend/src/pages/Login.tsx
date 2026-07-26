import { FormEvent, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth';

export function Login() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await login(String(form.get('username')), String(form.get('password')));
      navigate('/', { replace: true });
    } catch {
      setError('Credenciales inválidas.');
    }
  }
  if (user) return <Navigate to="/" replace />;
  return <main className="login-page"><form onSubmit={submit}>
    <h1>Ingreso académico</h1>
    <label>Usuario<input name="username" autoComplete="username" required /></label>
    <label>Contraseña<input name="password" type="password" autoComplete="current-password" required /></label>
    {error && <p role="alert">{error}</p>}
    <button type="submit">Ingresar</button>
  </form></main>;
}
