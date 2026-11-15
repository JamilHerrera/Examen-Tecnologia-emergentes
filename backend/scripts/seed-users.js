// Crea/actualiza los usuarios de demostracion. Las contrasenas vienen del .env (nunca del codigo).
import bcrypt from 'bcryptjs';
import '../src/config.js';
import { closePool, query } from '../src/db.js';

const users = [
  { username: 'admin', role: 'admin', password: process.env.DEMO_ADMIN_PASSWORD },
  { username: 'analyst', role: 'analyst', password: process.env.DEMO_ANALYST_PASSWORD },
];

for (const u of users) {
  if (!u.password) throw new Error(`Falta la contrasena demo de ${u.username} en .env`);
  const hash = await bcrypt.hash(u.password, 10);
  await query(
    `MERGE ops.app_user AS t USING (SELECT @u AS Username) AS s ON t.Username = s.Username
     WHEN MATCHED THEN UPDATE SET PasswordHash = @h, Role = @r, IsActive = 1
     WHEN NOT MATCHED THEN INSERT (Username, PasswordHash, Role) VALUES (@u, @h, @r);`,
    { u: u.username, h: hash, r: u.role },
  );
  console.log(`Usuario ${u.username} (${u.role}) listo`);
}
await closePool();
