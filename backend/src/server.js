import http from 'node:http';
import { createApp } from './app.js';
import { config } from './config.js';

const app = createApp();
const server = http.createServer(app);

server.listen(config.port, () => {
  console.log(`API escuchando en http://localhost:${config.port}`);
});
