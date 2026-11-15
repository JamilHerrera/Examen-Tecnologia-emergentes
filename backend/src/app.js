import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { config } from './config.js';
import { router } from './routes/api.js';
import { metricsMiddleware } from './metrics.js';

export function createApp() {
  const app = express();
  app.disable('x-powered-by');
  app.use(helmet());
  app.use(cors({ origin: config.corsOrigin }));
  app.use(express.json({ limit: '10kb' }));
  app.use(metricsMiddleware);
  app.use('/api', router);

  app.use('/api', (_req, res) => res.status(404).json({ error: 'Ruta no encontrada' }));

  // eslint-disable-next-line no-unused-vars
  app.use((err, _req, res, _next) => {
    if (err.status && err.status < 500) return res.status(err.status).json({ error: err.message });
    // Los detalles internos (SQL, rutas) se registran pero no se exponen al cliente.
    console.error('[error]', err);
    res.status(500).json({ error: 'Error interno del servidor' });
  });
  return app;
}
