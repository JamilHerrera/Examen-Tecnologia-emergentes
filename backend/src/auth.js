import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { config } from './config.js';
import { query } from './db.js';

const ROLE_RANK = { viewer: 1, analyst: 2, admin: 3 };

export async function login(username, password) {
  if (typeof username !== 'string' || typeof password !== 'string' || username.length > 50 || password.length > 200) {
    return null;
  }
  const rows = await query(
    'SELECT Username, PasswordHash, Role FROM ops.app_user WHERE Username = @u AND IsActive = 1',
    { u: username },
  );
  const user = rows[0];
  // Se compara siempre contra un hash para no revelar si el usuario existe por tiempos de respuesta.
  const hash = user?.PasswordHash ?? '$2a$10$invalidinvalidinvalidinvalidinvalidinvalidinvalidinvalid.';
  const ok = await bcrypt.compare(password, hash);
  if (!user || !ok) return null;
  const token = jwt.sign({ sub: user.Username, role: user.Role }, config.jwtSecret, {
    expiresIn: config.jwtExpiresIn,
  });
  return { token, user: { username: user.Username, role: user.Role } };
}

export function verifyToken(token) {
  try {
    const payload = jwt.verify(token, config.jwtSecret);
    return { username: payload.sub, role: payload.role };
  } catch {
    return null;
  }
}

export function authenticate(req, res, next) {
  const header = req.headers.authorization ?? '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : null;
  const user = token ? verifyToken(token) : null;
  if (!user) return res.status(401).json({ error: 'No autenticado' });
  req.user = user;
  next();
}

export function requireRole(minRole) {
  return (req, res, next) => {
    if ((ROLE_RANK[req.user?.role] ?? 0) < ROLE_RANK[minRole]) {
      return res.status(403).json({ error: 'Permisos insuficientes' });
    }
    next();
  };
}
