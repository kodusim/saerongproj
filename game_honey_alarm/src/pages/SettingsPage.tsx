import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { subscriptionAPI } from '../api/services';
import { useAuth } from '../hooks/useAuth';

export default function SettingsPage() {
  const navigate = useNavigate();
  const { user, isAuthenticated, logout, loading } = useAuth();

  const { data: subscriptions } = useQuery({
    queryKey: ['subscriptions'],
    queryFn: subscriptionAPI.getMySubscriptions,
    enabled: isAuthenticated,
  });

  return (
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto', paddingBottom: '80px' }}>
      {/* 헤더 */}
      <header style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>설정</h1>
      </header>

      {/* 로그인 정보 */}
      <div style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '16px' }}>
          계정
        </h2>
        {isAuthenticated ? (
          <div style={{
            padding: '16px',
            backgroundColor: '#f5f5f5',
            borderRadius: '12px',
          }}>
            <div style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '14px', color: '#666', marginBottom: '4px' }}>
                사용자 ID
              </div>
              <div style={{ fontSize: '16px', fontWeight: '500' }}>
                {user?.userKey || 'Unknown'}
              </div>
            </div>
            {user?.name && (
              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontSize: '14px', color: '#666', marginBottom: '4px' }}>
                  이름
                </div>
                <div style={{ fontSize: '16px', fontWeight: '500' }}>
                  {user.name}
                </div>
              </div>
            )}
            <button
              onClick={logout}
              disabled={loading}
              style={{
                marginTop: '12px',
                padding: '10px 20px',
                backgroundColor: '#e0e0e0',
                color: '#333',
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 'bold',
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.6 : 1,
              }}
            >
              {loading ? '로그아웃 중...' : '로그아웃'}
            </button>
          </div>
        ) : (
          <div style={{
            padding: '16px',
            backgroundColor: '#FFF9E6',
            borderRadius: '12px',
            textAlign: 'center',
          }}>
            <p style={{ marginBottom: '12px', color: '#666' }}>
              로그인하지 않았습니다.
            </p>
            <button
              onClick={() => navigate('/home')}
              style={{
                padding: '10px 20px',
                backgroundColor: '#FFB800',
                color: '#fff',
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 'bold',
                cursor: 'pointer',
              }}
            >
              홈으로 가기
            </button>
          </div>
        )}
      </div>

      {/* 구독 목록 */}
      {isAuthenticated && (
        <div style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '16px' }}>
            구독 목록
          </h2>
          {subscriptions && subscriptions.length > 0 ? (
            <div style={{ display: 'grid', gap: '8px' }}>
              {subscriptions.map((sub) => (
                <div
                  key={sub.id}
                  style={{
                    padding: '12px 16px',
                    backgroundColor: '#f5f5f5',
                    borderRadius: '8px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ fontSize: '15px', fontWeight: '500', marginBottom: '4px' }}>
                      {sub.game_id}
                    </div>
                    <div style={{ fontSize: '13px', color: '#666' }}>
                      {sub.category}
                    </div>
                  </div>
                  <button
                    onClick={() => navigate(`/game/${sub.game_id}`)}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: '#e0e0e0',
                      border: 'none',
                      borderRadius: '6px',
                      fontSize: '13px',
                      cursor: 'pointer',
                    }}
                  >
                    관리
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div style={{
              padding: '20px',
              backgroundColor: '#f5f5f5',
              borderRadius: '12px',
              textAlign: 'center',
            }}>
              <p style={{ color: '#999' }}>구독한 게임이 없습니다.</p>
            </div>
          )}
        </div>
      )}

      {/* 앱 정보 */}
      <div>
        <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '16px' }}>
          앱 정보
        </h2>
        <div style={{ display: 'grid', gap: '8px' }}>
          <div style={{
            padding: '12px 16px',
            backgroundColor: '#f5f5f5',
            borderRadius: '8px',
          }}>
            <div style={{ fontSize: '14px', color: '#666', marginBottom: '4px' }}>
              버전
            </div>
            <div style={{ fontSize: '15px' }}>1.0.0</div>
          </div>
          <div style={{
            padding: '12px 16px',
            backgroundColor: '#f5f5f5',
            borderRadius: '8px',
          }}>
            <div style={{ fontSize: '14px', color: '#666', marginBottom: '4px' }}>
              문의
            </div>
            <div style={{ fontSize: '15px' }}>farmhoney1298@naver.com</div>
          </div>
        </div>
      </div>

      {/* 하단 네비게이션 */}
      <nav style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        backgroundColor: '#fff',
        borderTop: '1px solid #e0e0e0',
        display: 'flex',
        justifyContent: 'space-around',
        padding: '12px 0',
      }}>
        <button
          onClick={() => navigate('/home')}
          style={{
            flex: 1,
            padding: '8px',
            backgroundColor: 'transparent',
            border: 'none',
            fontSize: '14px',
            color: '#666',
            cursor: 'pointer',
          }}
        >
          홈
        </button>
        <button
          onClick={() => navigate('/notifications')}
          style={{
            flex: 1,
            padding: '8px',
            backgroundColor: 'transparent',
            border: 'none',
            fontSize: '14px',
            color: '#666',
            cursor: 'pointer',
          }}
        >
          알림
        </button>
        <button
          onClick={() => navigate('/settings')}
          style={{
            flex: 1,
            padding: '8px',
            backgroundColor: 'transparent',
            border: 'none',
            fontSize: '14px',
            fontWeight: 'bold',
            color: '#FFB800',
            cursor: 'pointer',
          }}
        >
          설정
        </button>
      </nav>
    </div>
  );
}
