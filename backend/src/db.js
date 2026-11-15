import sql from 'mssql';
import { config } from './config.js';

let poolPromise;

export function getPool() {
  if (!poolPromise) {
    poolPromise = new sql.ConnectionPool(config.db).connect().catch((err) => {
      poolPromise = undefined;
      throw err;
    });
  }
  return poolPromise;
}

/**
 * Ejecuta SQL parametrizado. params: { nombre: valor } o { nombre: { type, value } }.
 * Nunca se concatenan valores del usuario dentro del texto SQL.
 */
export async function query(text, params = {}) {
  const pool = await getPool();
  const request = pool.request();
  for (const [name, p] of Object.entries(params)) {
    if (p && typeof p === 'object' && 'type' in p) request.input(name, p.type, p.value);
    else request.input(name, p);
  }
  const result = await request.query(text);
  return result.recordset ?? [];
}

export async function closePool() {
  if (poolPromise) {
    const pool = await poolPromise;
    await pool.close();
    poolPromise = undefined;
  }
}

export { sql };
