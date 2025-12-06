import react from '@vitejs/plugin-react';
import legacy from '@vitejs/plugin-legacy';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [
    react(),
    legacy({
      targets: ['defaults', 'not IE 11'],
    }),
  ],
  base: './',
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: 'https://saerong.com',
        changeOrigin: true,
        secure: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
  optimizeDeps: {
    entries: ['index.html'],
  },
});
