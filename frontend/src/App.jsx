import { useEffect, useState } from 'react';
import { api, auth, connectAlertSocket, fmt, useApi } from './api.js';
import Login from './pages/Login.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Operations from './pages/Operations.jsx';
import Assistant from './pages/Assistant.jsx';
import Alerts from './pages/Alerts.jsx';
import BusinessAnalytics from './pages/BusinessAnalytics.jsx';
import { Status } from './components/Common.jsx';

function Shell({ user, onLogout }) {
  const [tab, setTab] = useState('dashboard');
  const meta = useApi('/meta');
  const newAlerts = useApi('/alerts?status=new&limit=200');
  const [liveAlert, setLiveAlert] = useState(null);
  const [toast, setToast] = useState(null);
  const [socketState, setSocketState] = useState('disconnected');
  const [liveCount, setLiveCount] = useState(0);

  useEffect(() => connectAlertSocket((alert) => {
    setLiveAlert(alert);
    setLiveCount((c) => c + 1);
    setToast(alert);
    setTimeout(() => setToast(null), 8000);
  }, setSocketState), []);

  const badge = (newAlerts.data?.length ?? 0) + liveCount;
  const tabs = [
    ['dashboard', 'Dashboard'],
    ['business', 'Negocio'],
    ['alerts', `Alertas${badge ? ` (${badge})` : ''}`],
    ['assistant', 'Asistente IA'],
    ['ops', 'Operacion'],
  ];

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>WWI Analytics</h1>
          <span className="muted">
            Datos actualizados: {meta.data ? fmt.datetime(meta.data.freshness.lastLoadedAt) : '…'} ·
            alertas en vivo: {socketState === 'connected' ? 'conectado' : 'reconectando…'}
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
      {toast && (
        <div className="toast" role="alert">
          <strong>Nueva alerta {toast.severity.toUpperCase()}{toast.simulated ? ' (simulacion)' : ''}</strong>
          <span>{toast.indicator}{toast.entity ? ` · ${toast.entity}` : ''}</span>
          <button onClick={() => { setTab('alerts'); setToast(null); }}>Ver</button>
        </div>
      )}
      <main>
        <Status loading={meta.loading} error={meta.error} onRetry={meta.reload} height={200}>
          {meta.data && tab === 'dashboard' && <Dashboard meta={meta.data} />}
          {meta.data && tab === 'business' && <BusinessAnalytics meta={meta.data} />}
          {meta.data && tab === 'alerts' && <Alerts user={user} liveAlert={liveAlert} />}
          {meta.data && tab === 'assistant' && <Assistant />}
          {meta.data && tab === 'ops' && <Operations user={user} />}
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
    // Restaura la sesion desde el JWT guardado; el backend valida el token en cada llamada.
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
