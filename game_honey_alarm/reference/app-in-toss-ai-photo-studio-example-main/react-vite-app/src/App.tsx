import { Navigate, Route, Routes } from 'react-router-dom';
import ProfilePage from './pages/ProfilePage';

const PROFILE_PATH = '/profile';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to={PROFILE_PATH} replace />} />
      <Route path={PROFILE_PATH} element={<ProfilePage />} />
      <Route path="*" element={<Navigate to={PROFILE_PATH} replace />} />
    </Routes>
  );
}
