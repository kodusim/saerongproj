import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { gameAPI, notificationAPI } from '../api/services';
import type { Game } from '../types';
import { useAuth } from '../hooks/useAuth';

type Tab = 'home' | 'notifications' | 'settings';

export default function MainScreen() {
  const { isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<Tab>('home');
  const [games, setGames] = useState<Game[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  // 알림 피드 조회 (로그인 상태일 때만)
  const { data: notifications = [], isLoading: notificationsLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationAPI.getFeed(50),
    enabled: isAuthenticated && activeTab === 'notifications',
  });

  useEffect(() => {
    loadGames();
  }, []);

  const loadGames = async () => {
    try {
      const gameList = await gameAPI.getGames();
      setGames(gameList);
    } catch (error) {
      console.error('Failed to load games:', error);
    }
  };

  const filteredGames = games.filter((game) =>
    game.displayName.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <div style={{
        padding: '16px 24px',
        borderBottom: '1px solid #E5E8EB'
      }}>
        <h1 style={{
          fontSize: '24px',
          fontWeight: 'bold',
          margin: 0,
          marginBottom: '16px'
        }}>
          게임 허니
        </h1>

        {/* Search Input */}
        <input
          type="text"
          placeholder="게임명 검색"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{
            width: '100%',
            padding: '12px 16px',
            fontSize: '15px',
            border: '1px solid #E5E8EB',
            borderRadius: '8px',
            outline: 'none'
          }}
        />
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: '0 24px' }}>
        {activeTab === 'home' && (
          <div>
            {filteredGames.map((game) => (
              <div
                key={game.id}
                style={{
                  padding: '16px 0',
                  borderBottom: '1px solid #F2F4F6',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer'
                }}
                onClick={() => {
                  // TODO: 게임 상세 페이지로 이동
                  console.log('게임 클릭:', game.id);
                }}
              >
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                  <div style={{
                    width: '48px',
                    height: '48px',
                    backgroundColor: '#F2F4F6',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '10px',
                    color: '#8B95A1',
                    textAlign: 'center',
                    lineHeight: '1.2',
                    flexShrink: 0
                  }}>
                    이미지<br />준비중
                  </div>

                  <div>
                    <div style={{
                      fontSize: '16px',
                      fontWeight: '600',
                      marginBottom: '4px'
                    }}>
                      {game.displayName}
                    </div>
                    <div style={{
                      fontSize: '13px',
                      color: '#8B95A1'
                    }}>
                      {game.categories.join(', ')}
                    </div>
                  </div>
                </div>

                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M9 6L15 12L9 18"
                    stroke="#8B95A1"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
            ))}

            {filteredGames.length === 0 && (
              <div style={{
                textAlign: 'center',
                padding: '60px 20px',
                color: '#8B95A1'
              }}>
                {searchQuery ? '검색 결과가 없습니다' : '게임 목록을 불러오는 중...'}
              </div>
            )}
          </div>
        )}

        {activeTab === 'notifications' && (
          <div>
            {!isAuthenticated ? (
              <div style={{
                textAlign: 'center',
                padding: '60px 20px',
                color: '#8B95A1'
              }}>
                로그인 후 구독한 게임의 알림을 확인하세요
              </div>
            ) : notificationsLoading ? (
              <div style={{
                textAlign: 'center',
                padding: '60px 20px',
                color: '#8B95A1'
              }}>
                알림을 불러오는 중...
              </div>
            ) : notifications.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '60px 20px',
                color: '#8B95A1'
              }}>
                구독한 게임의 새 소식이 없습니다
              </div>
            ) : (
              notifications.map((notif, index) => (
                <div
                  key={`${notif.game_id}-${notif.category}-${index}`}
                  style={{
                    padding: '16px 0',
                    borderBottom: '1px solid #F2F4F6',
                    cursor: 'pointer'
                  }}
                  onClick={() => window.open(notif.url, '_blank')}
                >
                  <div style={{
                    fontSize: '12px',
                    color: '#8B95A1',
                    marginBottom: '4px'
                  }}>
                    {notif.game} · {notif.category}
                  </div>
                  <div style={{
                    fontSize: '15px',
                    fontWeight: '500',
                    marginBottom: '4px',
                    color: '#191F28'
                  }}>
                    {notif.title}
                  </div>
                  <div style={{
                    fontSize: '13px',
                    color: '#8B95A1'
                  }}>
                    {new Date(notif.date).toLocaleDateString()}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'settings' && (
          <div style={{
            textAlign: 'center',
            padding: '60px 20px',
            color: '#8B95A1'
          }}>
            설정 화면
          </div>
        )}
      </div>

      {/* Bottom Tab Navigation */}
      <div style={{
        display: 'flex',
        borderTop: '1px solid #E5E8EB',
        backgroundColor: 'white'
      }}>
        <button
          onClick={() => setActiveTab('home')}
          style={{
            flex: 1,
            padding: '12px',
            border: 'none',
            backgroundColor: 'transparent',
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '4px',
            borderTop: activeTab === 'home' ? '2px solid #FDB300' : '2px solid transparent',
            color: activeTab === 'home' ? '#FDB300' : '#8B95A1'
          }}
        >
          <span style={{ fontSize: '20px' }}>🏠</span>
          <span style={{ fontSize: '12px', fontWeight: activeTab === 'home' ? '600' : '400' }}>
            홈
          </span>
        </button>

        <button
          onClick={() => setActiveTab('notifications')}
          style={{
            flex: 1,
            padding: '12px',
            border: 'none',
            backgroundColor: 'transparent',
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '4px',
            borderTop: activeTab === 'notifications' ? '2px solid #FDB300' : '2px solid transparent',
            color: activeTab === 'notifications' ? '#FDB300' : '#8B95A1'
          }}
        >
          <span style={{ fontSize: '20px' }}>🔔</span>
          <span style={{ fontSize: '12px', fontWeight: activeTab === 'notifications' ? '600' : '400' }}>
            알림
          </span>
        </button>

        <button
          onClick={() => setActiveTab('settings')}
          style={{
            flex: 1,
            padding: '12px',
            border: 'none',
            backgroundColor: 'transparent',
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '4px',
            borderTop: activeTab === 'settings' ? '2px solid #FDB300' : '2px solid transparent',
            color: activeTab === 'settings' ? '#FDB300' : '#8B95A1'
          }}
        >
          <span style={{ fontSize: '20px' }}>⚙️</span>
          <span style={{ fontSize: '12px', fontWeight: activeTab === 'settings' ? '600' : '400' }}>
            설정
          </span>
        </button>
      </div>
    </div>
  );
}
