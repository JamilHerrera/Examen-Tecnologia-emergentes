import { WebSocketServer } from 'ws';
import { verifyToken } from '../auth.js';

let wss;

/** WebSocket /ws: el cliente se autentica con su primer mensaje {type:'auth', token}. */
export function setupWebSocket(server) {
  wss = new WebSocketServer({ server, path: '/ws', maxPayload: 4096 });
  wss.on('connection', (socket) => {
    socket.authed = false;
    const timer = setTimeout(() => !socket.authed && socket.close(4401, 'auth timeout'), 5000);
    socket.on('message', (raw) => {
      try {
        const msg = JSON.parse(raw.toString());
        const user = msg.type === 'auth' ? verifyToken(msg.token) : null;
        if (!user) return socket.close(4401, 'unauthorized');
        socket.authed = true;
        socket.send(JSON.stringify({ type: 'ready', user: user.username }));
      } catch {
        socket.close(4400, 'bad message');
      }
    });
    socket.on('close', () => clearTimeout(timer));
  });
  return wss;
}

/** Envia un evento a todos los clientes autenticados; devuelve cuantos lo recibieron. */
export function broadcast(payload) {
  if (!wss) return 0;
  const data = JSON.stringify(payload);
  let sent = 0;
  for (const client of wss.clients) {
    if (client.authed && client.readyState === 1) {
      client.send(data);
      sent += 1;
    }
  }
  return sent;
}

export function closeWebSocket() {
  wss?.close();
  wss = undefined;
}
