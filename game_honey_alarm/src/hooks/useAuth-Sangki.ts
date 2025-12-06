import { useState } from 'react';
import { appLogin } from '@apps-in-toss/web-framework';
import { useAuthStore } from '../store/authStore';
import { authAPI } from '../api/services';

export const useAuth = () => {
  const { user, isAuthenticated, login, logout: storeLogout } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 토스 로그인 실행
  const handleLogin = async () => {
    try {
      setLoading(true);
      setError(null);

      // 1. 앱인토스에서 authorizationCode 받기
      const { authorizationCode, referrer } = await appLogin();

      // 2. Django 백엔드로 전송하여 accessToken 받기
      const { accessToken } = await authAPI.login(authorizationCode, referrer);

      // 3. accessToken으로 사용자 정보 조회
      const userInfo = await authAPI.getUserInfo();

      // 4. 스토어에 저장
      login(userInfo, accessToken);
    } catch (err) {
      console.error('Login failed:', err);
      setError('로그인에 실패했습니다. 다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  };

  // 로그아웃
  const handleLogout = async () => {
    try {
      setLoading(true);
      await authAPI.logout();
      storeLogout();
    } catch (err) {
      console.error('Logout failed:', err);
      // 로그아웃은 실패해도 로컬 상태는 정리
      storeLogout();
    } finally {
      setLoading(false);
    }
  };

  return {
    user,
    isAuthenticated,
    loading,
    error,
    login: handleLogin,
    logout: handleLogout,
  };
};
