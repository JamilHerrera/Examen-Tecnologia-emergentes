import http from 'node:http';
import { createApp } from './app.js';
import { config } from './config.js';
import { setupWebSocket } from './services/ws.js';
import { startAlertScheduler } from './services/alerts.js';

const app = createApp();
const server = http.createServer(app);
setupWebSocket(server);

server.listen(config.port, () => {
  console.log(`API escuchando en http://localhost:${config.port}`);
  startAlertScheduler();
  console.log(`Evaluacion de alertas cada ${config.alerts.evalIntervalMinutes} min`);
});
