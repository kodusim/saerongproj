import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { notificationAPI } from '../api/services';
import { useAuth } from '../hooks/useAuth';

export default function NotificationFeedPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const { data: feed, isLoading } = useQuery({
    queryKey: ['notificationFeed'],
    queryFn: notificationAPI.getFeed,
    enabled: isAuthenticated,
  });

  if (!isAuthenticated) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p style={{ marginBottom: '16px', color: '#666' }}>
          로그인이 필요합니다.
        </p>
        <button
          onClick={() => navigate('/home')}
          style={{
            padding: '12px 24px',
            backgroundColor: '#FFB800',
            color: '#fff',
            border: 'none',
            borderRadius: '8px',
            fontSize: '16px',
            fontWeight: 'bold',
            cursor: 'pointer',
          }}
        >
          홈으로 가기
        </button>
      </div>
    );
  }

  if (isLoading) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>로딩 중...</div>;
  }

  return (
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto', paddingBottom: '80px' }}>
      {/* 헤더 */}
      <header style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>알림 피드</h1>
        <p style={{ marginTop: '4px', color: '#666', fontSize: '14px' }}>
          구독한 게임의 최신 소식
        </p>
      </header>

      {/* 알림 목록 */}
      <div style={{ display: 'grid', gap: '12px' }}>
        {feed && feed.length > 0 ? (
          feed.map((item: any, index: number) => (
            <a
              key={index}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: '16px',
                backgroundColor: '#fff',
                border: '1px solid #e0e0e0',
                borderRadius: '12px',
                textDecoration: 'none',
                color: '#333',
                display: 'block',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#FFB800';
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(255, 184, 0, 0.1)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#e0e0e0';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span
                  style={{
                    fontSize: '12px',
                    fontWeight: 'bold',
                    color: '#FFB800',
                    backgroundColor: '#FFF9E6',
                    padding: '4px 8px',
                    borderRadius: '4px',
                  }}
                >
                  {item.game} · {item.category}
                </span>
                <span style={{ fontSize: '12px', color: '#999' }}>
                  {new Date(item.date).toLocaleDateString()}
                </span>
              </div>
              <div style={{ fontSize: '15px', fontWeight: '500', lineHeight: '1.5' }}>
                {item.title}
              </div>
            </a>
          ))
        ) : (
          <div style={{ textAlign: 'center', padding: '40px 20px' }}>
            <p style={{ fontSize: '16px', color: '#999', marginBottom: '16px' }}>
              아직 구독한 게임이 없습니다.
            </p>
            <button
              onClick={() => navigate('/home')}
              style={{
                padding: '12px 24px',
                backgroundColor: '#FFB800',
                color: '#fff',
                border: 'none',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 'bold',
                cursor: 'pointer',
              }}
            >
              게임 구독하러 가기
            </button>
          </div>
        )}
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
            fontWeight: 'bold',
            color: '#FFB800',
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
            color: '#666',
            cursor: 'pointer',
          }}
        >
          설정
        </button>
      </nav>
    </div>
  );
}
