import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// El navegador solo habla con el backend (proxy /api y /ws); nunca con SQL Server.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:4000',
      '/ws': { target: 'ws://localhost:4000', ws: true },
    },
  },
});
