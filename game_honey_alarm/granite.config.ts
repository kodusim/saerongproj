import { defineConfig } from '@apps-in-toss/web-framework/config';

export default defineConfig({
  appName: 'gamehoney',
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
  brand: {
    displayName: '게임 하니',
    icon: 'https://static.toss.im/appsintoss/6735/aa394266-f7f7-4184-bbbc-ba8809b31734.png',
    primaryColor: '#FDB300',
    bridgeColorMode: 'basic',
  },
});
