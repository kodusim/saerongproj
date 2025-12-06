import { StrictMode } from 'react';
import ReactDOM from 'react-dom/client';
import { ThemeProvider } from '@toss/tds-mobile';
import ProfilePage from './pages/ProfilePage';
import './index.css';

// 앱 시작 시 초기 history state 추가
window.history.pushState({ page: 'init' }, '', '');

ReactDOM.createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <ProfilePage />
    </ThemeProvider>
  </StrictMode>
);
