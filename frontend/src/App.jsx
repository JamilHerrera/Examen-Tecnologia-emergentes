import { useEffect, useState } from 'react';
import { api, auth, fmt, useApi } from './api.js';
import Login from './pages/Login.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Operations from './pages/Operations.jsx';
import { Status } from './components/Common.jsx';

function Shell({ user, onLogout }) {
  const [tab, setTab] = useState('dashboard');
  const meta = useApi('/meta');
  const tabs = [['dashboard', 'Dashboard'], ['ops', 'Operacion']];

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>WWI Analytics</h1>
          <span className="muted">
            Datos actualizados: {meta.data ? fmt.datetime(meta.data.freshness.lastLoadedAt) : '…'}
          </span>
        </div>
        <nav aria-label="Secciones">
          {tabs.map(([id, label]) => (
            <button key={id} className={tab === id ? 'tab active' : 'tab'} onClick={() => setTab(id)}>{label}</button>
          ))}
        </nav>
        <div className="user">
          <span>{user.username} ({user.role})</span>
          <button onClick={onLogout}>Salir</button>
        </div>
      </header>
      <main>
        <Status loading={meta.loading} error={meta.error} onRetry={meta.reload} height={200}>
          {meta.data && (tab === 'dashboard' ? <Dashboard meta={meta.data} /> : <Operations user={user} />)}
        </Status>
      </main>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(Boolean(auth.token));

  const logout = () => { auth.token = null; setUser(null); };

  useEffect(() => {
    auth.onUnauthorized(logout);
    if (!auth.token) return;
    // Restaura la sesion decodificando el payload del JWT (la validacion real la hace el backend).
    try {
      const payload = JSON.parse(atob(auth.token.split('.')[1]));
      setUser({ username: payload.sub, role: payload.role });
      api('/health').catch(() => {});
    } catch {
      auth.token = null;
    }
    setChecking(false);
  }, []);

  if (checking) return null;
  return user ? <Shell user={user} onLogout={logout} /> : <Login onLogin={setUser} />;
}
