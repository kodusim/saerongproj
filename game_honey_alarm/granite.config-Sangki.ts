import { defineConfig } from '@apps-in-toss/web-framework/config';

export default defineConfig({
  appName: 'gamehoney',
  brand: {
    displayName: 'Game Honey',
    icon: '',
    primaryColor: '#FFB800',
    bridgeColorMode: 'basic',
  },
  web: {
    host: 'localhost',
    port: 5173,
    commands: {
      dev: 'vite --host',
      build: 'vite build',
    },
  },
  permissions: [],
  outdir: 'dist',
});
