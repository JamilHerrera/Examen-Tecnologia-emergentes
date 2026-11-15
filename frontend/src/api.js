import { useCallback, useEffect, useRef, useState } from 'react';

const TOKEN_KEY = 'wwi_token';
let onUnauthorized = () => {};

export const auth = {
  get token() { return sessionStorage.getItem(TOKEN_KEY); },
  set token(v) { v ? sessionStorage.setItem(TOKEN_KEY, v) : sessionStorage.removeItem(TOKEN_KEY); },
  onUnauthorized(fn) { onUnauthorized = fn; },
};

export async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch(`/api${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(auth.token ? { Authorization: `Bearer ${auth.token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && path !== '/auth/login') onUnauthorized();
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Error ${res.status}`);
  return data;
}

export function toQuery(params) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => v !== undefined && v !== '' && v !== null && q.set(k, v));
  return q.toString();
}

/** Carga datos con estados loading / error / data y evita respuestas obsoletas. */
export function useApi(path, deps = []) {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const seq = useRef(0);
  const load = useCallback(() => {
    if (!path) return;
    const id = ++seq.current;
    setState((s) => ({ ...s, loading: true, error: null }));
    api(path)
      .then((data) => id === seq.current && setState({ loading: false, error: null, data }))
      .catch((error) => id === seq.current && setState({ loading: false, error: error.message, data: null }));
  }, [path]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [load, ...deps]);
  return { ...state, reload: load };
}

/** Conecta al WebSocket de alertas (autenticacion con el primer mensaje) y reconecta si se cae. */
export function connectAlertSocket(onAlert, onState = () => {}) {
  let socket;
  let closed = false;
  let retry;
  const open = () => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    socket = new WebSocket(`${proto}://${location.host}/ws`);
    socket.onopen = () => socket.send(JSON.stringify({ type: 'auth', token: auth.token }));
    socket.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === 'ready') onState('connected');
      if (msg.type === 'alert') onAlert(msg.alert);
    };
    socket.onclose = () => {
      onState('disconnected');
      if (!closed) retry = setTimeout(open, 5000);
    };
  };
  open();
  return () => { closed = true; clearTimeout(retry); socket?.close(); };
}

export const fmt = {
  money: (v) => (v == null ? '—' : new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(v)),
  money2: (v) => (v == null ? '—' : new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(v)),
  int: (v) => (v == null ? '—' : new Intl.NumberFormat('en-US').format(Math.round(v))),
  pct: (v) => (v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`),
  compact: (v) => new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(v),
  datetime: (v) => (v ? new Date(v).toLocaleString('es') : '—'),
};
