import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const allowedHosts = (process.env.VITE_ALLOWED_HOSTS ?? '')
  .split(',')
  .map((host) => host.trim())
  .filter(Boolean);

export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_PUBLIC_BASE_PATH || '/',
  server: {
    port: 5173,
    allowedHosts,
  },
});
