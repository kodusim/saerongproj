import { defineConfig } from '@apps-in-toss/web-framework/config';

export default defineConfig({
  appName: 'ai-photo-studio',
  brand: {
    displayName: 'AI 사진관',
    icon: 'https://yourdomain.com/logo.png?v=1',
    primaryColor: '#3182F6',
    bridgeColorMode: 'basic', // 또는 'inverted'로 변경 가능
  },
  navigationBar: {
    withBackButton: true,
    withHomeButton: true,
  },
  permissions: [
    { name: 'camera', access: 'access' },
    { name: 'photos', access: 'read' },
  ],
  web: {
    host: '172.1.1.85', // 실기기에서 접근할 수 있는 IP 주소
    port: 5173,
    commands: {
      dev: 'vite --host',
      build: 'vite build',
    },
  },
  outdir: 'dist',
});
