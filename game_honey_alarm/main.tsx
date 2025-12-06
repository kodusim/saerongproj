import { StrictMode } from 'react';
import ReactDOM from 'react-dom/client';
import { ThemeProvider } from '@toss/tds-mobile';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProfilePage from './src/pages/ProfilePage';
import './src/index.css';
import VConsole from 'vconsole';

// 디버깅을 위한 vConsole 초기화 (배포 환경에서도 사용)
new VConsole();

// React Query 클라이언트 생성
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// 앱 시작 시 초기 history state 추가
window.history.pushState({ page: 'init' }, '', '');

ReactDOM.createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ProfilePage />
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>
);
