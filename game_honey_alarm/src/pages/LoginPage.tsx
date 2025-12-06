import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useEffect } from 'react';
import { useAuthStore } from '../store/authStore';

export default function LoginPage() {
  const navigate = useNavigate();
  const { isAuthenticated, login, loading, error } = useAuth();
  const authStore = useAuthStore();

  // 이미 로그인되어 있으면 홈으로 이동
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/home');
    }
  }, [isAuthenticated, navigate]);

  // 개발 환경에서 테스트용 로그인
  const handleMockLogin = () => {
    const mockUser = {
      userKey: 123456,
      name: '테스트 사용자',
      email: 'test@example.com',
    };
    const mockToken = 'mock-access-token-for-dev';

    authStore.login(mockUser, mockToken);
    navigate('/home');
  };

  const handleLogin = async () => {
    // 개발 환경에서는 목 로그인 사용
    if (import.meta.env.DEV) {
      handleMockLogin();
      return;
    }

    // 실제 토스 앱 환경에서만 실제 로그인 시도
    await login();
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        padding: '20px',
        textAlign: 'center',
      }}
    >
      {/* 로고 */}
      <div style={{ marginBottom: '40px' }}>
        <div
          style={{
            width: '80px',
            height: '80px',
            backgroundColor: '#FFB800',
            borderRadius: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '40px',
            fontWeight: 'bold',
            color: '#fff',
            margin: '0 auto',
          }}
        >
          GH
        </div>
      </div>

      {/* 타이틀 */}
      <h1
        style={{
          fontSize: '28px',
          fontWeight: 'bold',
          marginBottom: '12px',
          color: '#191F28',
        }}
      >
        Game Honey
      </h1>
      <p
        style={{
          fontSize: '16px',
          color: '#666',
          marginBottom: '60px',
        }}
      >
        좋아하는 게임의 소식을 놓치지 마세요
      </p>

      {/* 에러 메시지 */}
      {error && (
        <div
          style={{
            padding: '12px 20px',
            backgroundColor: '#ffebee',
            borderRadius: '8px',
            marginBottom: '20px',
            color: '#c62828',
            fontSize: '14px',
          }}
        >
          {error}
        </div>
      )}

      {/* 로그인 버튼 */}
      <button
        onClick={handleLogin}
        disabled={loading}
        style={{
          width: '100%',
          maxWidth: '320px',
          padding: '16px',
          backgroundColor: loading ? '#ccc' : '#FFB800',
          color: '#fff',
          border: 'none',
          borderRadius: '12px',
          fontSize: '18px',
          fontWeight: 'bold',
          cursor: loading ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s',
        }}
      >
        {loading ? '로그인 중...' : '토스로 시작하기'}
      </button>

      {/* 안내 문구 */}
      <p
        style={{
          fontSize: '13px',
          color: '#999',
          marginTop: '20px',
          lineHeight: '1.5',
        }}
      >
        토스 계정으로 간편하게 시작할 수 있어요
      </p>
    </div>
  );
}
