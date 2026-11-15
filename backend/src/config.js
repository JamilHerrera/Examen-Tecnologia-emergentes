import dotenv from 'dotenv';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
// El .env vive en la raiz del repositorio y no se versiona.
dotenv.config({ path: path.resolve(here, '../../.env') });

function required(name) {
  const v = process.env[name];
  if (!v) throw new Error(`Falta la variable de entorno ${name} (ver .env.example)`);
  return v;
}

const server = process.env.MSSQL_SERVER || 'localhost,1433';
const [host, port] = server.split(',');

export const config = {
  port: Number(process.env.BACKEND_PORT || 4000),
  corsOrigin: process.env.CORS_ORIGIN || 'http://localhost:5173',
  jwtSecret: required('JWT_SECRET'),
  jwtExpiresIn: '8h',
  db: {
    server: host,
    port: Number(port || 1433),
    database: process.env.MSSQL_DATABASE || 'WideWorldImporters',
    user: required('APP_DB_USER'),
    password: required('APP_DB_PASSWORD'),
    options: { encrypt: false, trustServerCertificate: true },
    pool: { max: 10, min: 0, idleTimeoutMillis: 30000 },
    requestTimeout: 30000,
  },
  ollama: {
    url: process.env.OLLAMA_URL || 'http://localhost:11434',
    model: process.env.OLLAMA_MODEL || 'qwen2.5:3b',
    timeoutMs: Number(process.env.OLLAMA_TIMEOUT_MS || 120000),
  },
  smtp: {
    host: process.env.SMTP_HOST || '',
    port: Number(process.env.SMTP_PORT || 587),
    user: process.env.SMTP_USER || '',
    password: process.env.SMTP_PASSWORD || '',
    to: process.env.ALERT_EMAIL_TO || '',
  },
  alerts: {
    evalIntervalMinutes: Number(process.env.ALERT_EVAL_INTERVAL_MIN || 15),
    salesDropThresholdPct: Number(process.env.ALERT_SALES_DROP_PCT || 15),
    forecastBelowPct: Number(process.env.ALERT_FORECAST_BELOW_PCT || 85),
    emailRetries: 3,
  },
};
