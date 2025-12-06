import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import IntroScreen from './IntroScreen';
import MainScreen from './MainScreen';

export default function ProfilePage() {
  const [showIntro, setShowIntro] = useState(true);
  const { isAuthenticated } = useAuth();

  if (showIntro && !isAuthenticated) {
    return <IntroScreen onNext={() => setShowIntro(false)} />;
  }

  return <MainScreen />;
}
