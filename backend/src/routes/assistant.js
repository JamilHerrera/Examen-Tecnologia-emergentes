import { Router } from 'express';
import rateLimit from 'express-rate-limit';
import { ask } from '../assistant/service.js';
import { ollamaStatus } from '../assistant/ollama.js';

export const assistantRouter = Router();

// Maximo 10 preguntas por minuto y por usuario (el router ya exige autenticacion).
const limiter = rateLimit({
  windowMs: 60_000,
  limit: 10,
  keyGenerator: (req) => req.user.username,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Demasiadas preguntas. Espera un minuto.' },
});

assistantRouter.get('/status', async (_req, res) => res.json(await ollamaStatus()));

assistantRouter.post('/ask', limiter, async (req, res, next) => {
  try {
    res.json(await ask({ username: req.user.username, question: req.body?.question }));
  } catch (err) {
    next(err);
  }
});
