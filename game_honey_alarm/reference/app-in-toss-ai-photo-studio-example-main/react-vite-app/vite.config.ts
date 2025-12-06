import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'configure-server',
      configureServer(server) {
        // HTTP 서버의 최대 헤더 크기 증가
        server.httpServer?.on('listening', () => {
          const httpServer = server.httpServer as any;
          if (httpServer?.maxHeadersCount !== undefined) {
            httpServer.maxHeadersCount = 0; // 무제한
          }
        });
      },
    },
  ],
  server: {
    host: '0.0.0.0',
    port: 5173,
    ws: {
      perMessageDeflate: false,
    },
  },
});
