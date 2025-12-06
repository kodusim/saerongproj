import { Navigate, Route, Routes } from 'react-router-dom';
import ProfilePage from './pages/ProfilePage';
import GameDetailPage from './pages/GameDetailPage';
import DebugConsole from './components/DebugConsole';

const PROFILE_PATH = '/profile';

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Navigate to={PROFILE_PATH} replace />} />
        <Route path={PROFILE_PATH} element={<ProfilePage />} />
        <Route path="/game/:gameId" element={<GameDetailPage />} />
        <Route path="*" element={<Navigate to={PROFILE_PATH} replace />} />
      </Routes>
      <DebugConsole />
    </>
  );
}
