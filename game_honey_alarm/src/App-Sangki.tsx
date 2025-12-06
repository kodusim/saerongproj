import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import IntroPage from './pages/IntroPage';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import GameDetailPage from './pages/GameDetailPage';
import NotificationFeedPage from './pages/NotificationFeedPage';
import SettingsPage from './pages/SettingsPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<IntroPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/game/:gameId" element={<GameDetailPage />} />
        <Route path="/notifications" element={<NotificationFeedPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
