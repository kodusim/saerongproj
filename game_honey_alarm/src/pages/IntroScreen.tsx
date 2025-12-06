import { useAuth } from '../hooks/useAuth';

interface IntroScreenProps {
  onNext: () => void;
}

export default function IntroScreen({ onNext }: IntroScreenProps) {
  const { login, loading, error } = useAuth();

  const handleLogin = async () => {
    await login();
    // 로그인 성공 시 onNext 호출 (에러가 없으면 자동으로 isAuthenticated가 true가 되어 MainScreen으로 이동)
    if (!error) {
      onNext();
    }
  };

  return (
    <div style={{
      padding: '24px',
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      justifyContent: 'space-between'
    }}>
      <div>
        {/* 로고 */}
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          marginTop: '40px',
          marginBottom: '40px'
        }}>
          <div style={{
            width: '80px',
            height: '80px',
            backgroundColor: '#FDB300',
            borderRadius: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '36px',
            fontWeight: 'bold',
            color: 'white'
          }}>
            GH
          </div>
        </div>

        {/* 메인 타이틀 */}
        <h1 style={{
          fontSize: '24px',
          fontWeight: 'bold',
          textAlign: 'center',
          marginBottom: '60px',
          lineHeight: '1.4'
        }}>
          내가 원하는 게임의 소식을<br />알림으로
        </h1>

        {/* 게임 아이콘과 설명 */}
        <div style={{
          backgroundColor: '#F8F9FA',
          borderRadius: '12px',
          padding: '32px 24px',
          textAlign: 'center',
          marginBottom: '40px'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🎮</div>
          <div style={{ fontSize: '16px', color: '#4E5968' }}>
            게임 소식을 한눈에
          </div>
        </div>

        {/* 게임 알림 받는법 */}
        <div>
          <h2 style={{
            fontSize: '18px',
            fontWeight: 'bold',
            marginBottom: '16px'
          }}>
            게임 알림 받는법
          </h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                backgroundColor: '#FDB300',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontWeight: 'bold',
                fontSize: '14px',
                flexShrink: 0
              }}>
                1
              </div>
              <span style={{ fontSize: '15px' }}>원하는 게임 검색</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                backgroundColor: '#FDB300',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontWeight: 'bold',
                fontSize: '14px',
                flexShrink: 0
              }}>
                2
              </div>
              <span style={{ fontSize: '15px' }}>원하는 소식 체크</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                backgroundColor: '#FDB300',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontWeight: 'bold',
                fontSize: '14px',
                flexShrink: 0
              }}>
                3
              </div>
              <span style={{ fontSize: '15px' }}>알림 받기</span>
            </div>
          </div>
        </div>
      </div>

      {/* 에러 메시지 */}
      {error && (
        <div style={{
          padding: '12px',
          backgroundColor: '#FFF0F0',
          borderRadius: '8px',
          color: '#E03E3E',
          fontSize: '14px',
          marginBottom: '16px',
          textAlign: 'center'
        }}>
          {error}
        </div>
      )}

      {/* 로그인 버튼 */}
      <button
        onClick={handleLogin}
        disabled={loading}
        style={{
          width: '100%',
          padding: '16px',
          backgroundColor: loading ? '#B0B8C1' : '#3182F6',
          color: 'white',
          fontSize: '16px',
          fontWeight: 'bold',
          border: 'none',
          borderRadius: '12px',
          marginBottom: '20px',
          cursor: loading ? 'not-allowed' : 'pointer',
          touchAction: 'manipulation'
        }}
      >
        {loading ? '로그인 중...' : '토스로 로그인'}
      </button>
    </div>
  );
}
