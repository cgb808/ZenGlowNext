import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
  root: '.',
  build: {
    sourcemap: true,
    emptyOutDir: true,
    outDir: '../app/static/dashboard',
  },
  server: {
    port: 5173,
    proxy: {
      '/inference': 'http://localhost:8001',
      '/metrics': 'http://localhost:8001',
      '/profiles': 'http://localhost:8001'
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  }
});
