import { Navigate, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import IntroPage from './pages/IntroPage';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import GameDetailPage from './pages/GameDetailPage';
import NotificationFeedPage from './pages/NotificationFeedPage';
import SettingsPage from './pages/SettingsPage';
import ProfilePage from './pages/ProfilePage';

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Routes>
        <Route path="/" element={<IntroPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/game/:gameId" element={<GameDetailPage />} />
        <Route path="/notifications" element={<NotificationFeedPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </QueryClientProvider>
  );
}
