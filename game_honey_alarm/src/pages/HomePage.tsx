import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ListRow } from '@toss/tds-mobile';
import { colors } from '@toss/tds-colors';
import { gameAPI } from '../api/services';
import { useAuth } from '../hooks/useAuth';
import { Spacing } from '../components/Spacing';

export default function HomePage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');

  const { data: games, isLoading } = useQuery({
    queryKey: ['games'],
    queryFn: gameAPI.getGames,
  });

  // 검색 필터링
  const filteredGames = games?.filter((game) =>
    game.displayName.toLowerCase().includes(searchQuery.toLowerCase()) ||
    game.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const styles = {
    container: {
      minHeight: '100vh',
      paddingBottom: '80px',
      backgroundColor: colors.white,
    },
    header: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '16px 20px',
      backgroundColor: colors.white,
      borderBottom: `1px solid ${colors.grey100}`,
    },
    headerTitle: {
      fontSize: '18px',
      fontWeight: 600,
      color: colors.grey900,
    },
    searchContainer: {
      padding: '20px',
      backgroundColor: colors.white,
    },
    searchInput: {
      width: '100%',
      padding: '14px 16px',
      fontSize: '16px',
      border: `1px solid ${colors.grey200}`,
      borderRadius: '8px',
      outline: 'none',
    },
    emptyState: {
      padding: '60px 20px',
      textAlign: 'center' as const,
    },
    emptyText: {
      fontSize: '16px',
      color: colors.grey600,
      marginTop: '12px',
    },
    loginBanner: {
      margin: '20px',
      padding: '20px',
      backgroundColor: '#FFF9E6',
      borderRadius: '12px',
      textAlign: 'center' as const,
    },
    loginText: {
      fontSize: '15px',
      color: colors.grey800,
      marginBottom: '16px',
    },
    imagePlaceholder: {
      width: '48px',
      height: '48px',
      backgroundColor: colors.grey100,
      borderRadius: '8px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '11px',
      color: colors.grey600,
      textAlign: 'center' as const,
      lineHeight: 1.2,
    },
    bottomNav: {
      position: 'fixed' as const,
      bottom: 0,
      left: 0,
      right: 0,
      backgroundColor: colors.white,
      borderTop: `1px solid ${colors.grey100}`,
      display: 'flex',
      justifyContent: 'space-around',
      padding: '12px 0',
    },
    navButton: {
      flex: 1,
      padding: '8px',
      backgroundColor: 'transparent',
      border: 'none',
      fontSize: '14px',
      cursor: 'pointer',
    },
  };

  if (isLoading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p style={{ color: colors.grey600 }}>로딩 중...</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* 헤더 */}
      <header style={styles.header}>
        <h1 style={styles.headerTitle}>게임 하니</h1>
      </header>

      {/* 로그인 배너 */}
      {!isAuthenticated && (
        <div style={styles.loginBanner}>
          <p style={styles.loginText}>
            로그인하고 게임 소식 알림을 받아보세요
          </p>
          <button
            onClick={() => navigate('/login')}
            style={{
              padding: '12px 24px',
              backgroundColor: '#FFB800',
              color: colors.white,
              border: 'none',
              borderRadius: '8px',
              fontSize: '15px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            토스로 로그인
          </button>
        </div>
      )}

      {/* 검색창 */}
      <div style={styles.searchContainer}>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="게임명 검색"
          style={styles.searchInput}
        />
      </div>

      <Spacing size={12} />

      {/* 게임 목록 */}
      <div>
        {filteredGames && filteredGames.length > 0 ? (
          filteredGames.map((game) => (
            <ListRow
              key={game.id}
              onClick={() => navigate(`/game/${game.id}`)}
              left={
                <div style={styles.imagePlaceholder}>
                  이미지
                  <br />
                  준비중
                </div>
              }
              contents={
                <div>
                  <div
                    style={{
                      fontSize: '16px',
                      fontWeight: 600,
                      color: colors.grey900,
                      marginBottom: '4px',
                    }}
                  >
                    {game.displayName}
                  </div>
                  <div
                    style={{
                      fontSize: '13px',
                      color: colors.grey600,
                    }}
                  >
                    {game.categories.join(', ')}
                  </div>
                </div>
              }
              withArrow={true}
            />
          ))
        ) : (
          <div style={styles.emptyState}>
            <div style={{ fontSize: '48px' }}>🔍</div>
            <p style={styles.emptyText}>
              {searchQuery ? '검색 결과가 없습니다' : '게임을 검색해보세요'}
            </p>
          </div>
        )}
      </div>

      {/* 하단 네비게이션 */}
      <nav style={styles.bottomNav}>
        <button
          onClick={() => navigate('/home')}
          style={{
            ...styles.navButton,
            fontWeight: 600,
            color: '#FFB800',
          }}
        >
          홈
        </button>
        <button
          onClick={() => navigate('/notifications')}
          style={{
            ...styles.navButton,
            color: colors.grey600,
          }}
        >
          알림
        </button>
        <button
          onClick={() => navigate('/settings')}
          style={{
            ...styles.navButton,
            color: colors.grey600,
          }}
        >
          설정
        </button>
      </nav>
    </div>
  );
}
