import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { GoogleAdMob, IAP } from '@apps-in-toss/web-framework';
import { gameAPI, notificationAPI, subscriptionAPI } from '../api/services';
import type { Game } from '../types';
import { useAuth } from '../hooks/useAuth';
import SettingsScreen from './SettingsScreen';

const AD_GROUP_ID = 'ait-ad-test-rewarded-id'; // 테스트용 광고 ID (프로덕션에서는 실제 ID로 변경)

type Tab = 'home' | 'notifications' | 'settings';

export default function MainScreen() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<Tab>('home');
  const [games, setGames] = useState<Game[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [adLoadStatus, setAdLoadStatus] = useState<'not_loaded' | 'loaded' | 'failed'>('not_loaded');
  const [isAdLoading, setIsAdLoading] = useState(false);
  const [isPurchasing, setIsPurchasing] = useState(false);
  const [showCancelDialog, setShowCancelDialog] = useState(false);

  // 알림 피드 조회 (로그인 상태일 때만)
  const { data: notifications = [], isLoading: notificationsLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationAPI.getFeed(50),
    enabled: isAuthenticated && activeTab === 'notifications',
  });

  // 프리미엄 구독 상태 조회
  const { data: premiumStatus, refetch: refetchPremiumStatus } = useQuery({
    queryKey: ['premiumStatus'],
    queryFn: subscriptionAPI.getPremiumStatus,
    enabled: isAuthenticated,
  });

  useEffect(() => {
    loadGames();
  }, []);

  // 광고 미리 로드
  useEffect(() => {
    if (!isAuthenticated || !GoogleAdMob.loadAppsInTossAdMob.isSupported()) {
      return;
    }

    const cleanup = GoogleAdMob.loadAppsInTossAdMob({
      options: {
        adGroupId: AD_GROUP_ID,
      },
      onEvent: (event) => {
        console.log('광고 로드 이벤트:', event.type);
        if (event.type === 'loaded') {
          console.log('광고 로드 성공');
          setAdLoadStatus('loaded');
        }
      },
      onError: (error) => {
        console.error('광고 로드 실패:', error);
        setAdLoadStatus('failed');
      },
    });

    return cleanup;
  }, [isAuthenticated]);

  const loadGames = async () => {
    try {
      const gameList = await gameAPI.getGames();
      setGames(gameList);
    } catch (error) {
      console.error('Failed to load games:', error);
    }
  };

  // 구독 취소
  const handleCancelSubscription = useCallback(async () => {
    setShowCancelDialog(false);
    try {
      await subscriptionAPI.cancelPremium();
      await refetchPremiumStatus();
      alert('구독이 취소되었습니다.');
    } catch (error) {
      console.error('구독 취소 실패:', error);
      alert('구독 취소에 실패했습니다.');
    }
  }, [refetchPremiumStatus]);

  // 광고 보고 7일 구독권 얻기
  const handleWatchAd = useCallback(() => {
    if (!GoogleAdMob.showAppsInTossAdMob.isSupported()) {
      alert('광고 기능이 지원되지 않는 환경입니다.');
      return;
    }

    if (adLoadStatus !== 'loaded') {
      alert('광고를 불러오는 중입니다. 잠시 후 다시 시도해주세요.');
      return;
    }

    // 프리미엄 구독 중이면 광고 시청 불가
    if (premiumStatus?.subscriptionType === 'premium') {
      return;
    }

    setIsAdLoading(true);

    GoogleAdMob.showAppsInTossAdMob({
      options: {
        adGroupId: AD_GROUP_ID,
      },
      onEvent: async (event) => {
        console.log('광고 이벤트:', event.type);

        if (event.type === 'userEarnedReward') {
          console.log('광고 시청 완료! 7일 구독권 부여');
          try {
            await subscriptionAPI.grantPremium('free_ad');
            await refetchPremiumStatus();
            alert('7일 무료 구독권이 발급되었습니다!');
            // 다음 광고 미리 로드
            setAdLoadStatus('not_loaded');
          } catch (error) {
            console.error('구독권 발급 실패:', error);
            alert('구독권 발급에 실패했습니다. 다시 시도해주세요.');
          } finally {
            setIsAdLoading(false);
          }
        } else if (event.type === 'dismissed') {
          console.log('광고 닫힘');
          setIsAdLoading(false);
        } else if (event.type === 'failedToShow') {
          console.log('광고 표시 실패');
          alert('광고 표시에 실패했습니다.');
          setIsAdLoading(false);
        }
      },
      onError: (error) => {
        console.error('광고 표시 오류:', error);
        alert('광고 표시 중 오류가 발생했습니다.');
        setIsAdLoading(false);
      },
    });
  }, [adLoadStatus, premiumStatus, refetchPremiumStatus]);

  // 프리미엄 구독권 구매하기
  const handlePurchasePremium = useCallback(async () => {
    console.log('IAP 객체:', IAP);
    console.log('IAP.getProductItemList:', IAP?.getProductItemList);

    if (!IAP || !IAP.getProductItemList) {
      console.error('IAP 기능을 사용할 수 없습니다. IAP:', IAP);
      alert('인앱결제 기능이 지원되지 않는 환경입니다.');
      return;
    }

    // 프리미엄 구독 중이면 구매 불가
    if (premiumStatus?.subscriptionType === 'premium') {
      alert('이미 프리미엄 구독권을 보유하고 있습니다.');
      return;
    }

    // 광고 구독 중이면 업그레이드 안내
    if (premiumStatus?.subscriptionType === 'free_ad') {
      if (!window.confirm('프리미엄 구독권을 구매하시면 광고 구독권이 자동으로 취소됩니다.\n계속하시겠습니까?')) {
        return;
      }
    }

    try {
      setIsPurchasing(true);

      // 상품 목록 조회
      const response = await IAP.getProductItemList();
      const products = response?.products ?? [];

      if (products.length === 0) {
        alert('구매 가능한 상품이 없습니다.');
        return;
      }

      // 첫 번째 상품 구매 (프리미엄 구독권)
      const product = products[0];

      IAP.createOneTimePurchaseOrder({
        options: {
          sku: product.sku,
          processProductGrant: async ({ orderId }) => {
            console.log('결제 완료, 구독권 발급:', orderId);
            try {
              await subscriptionAPI.grantPremium('premium', orderId);
              await refetchPremiumStatus();
              return true;
            } catch (error) {
              console.error('구독권 발급 실패:', error);
              return false;
            }
          },
        },
        onEvent: (event) => {
          console.log('인앱결제 이벤트:', event.type);
          if (event.type === 'success') {
            alert('프리미엄 구독권이 발급되었습니다!');
            setIsPurchasing(false);
          }
        },
        onError: (error) => {
          console.error('인앱결제 오류:', error);
          alert('결제에 실패했습니다.');
          setIsPurchasing(false);
        },
      });
    } catch (error) {
      console.error('상품 조회 실패:', error);
      alert('상품 정보를 불러오는데 실패했습니다.');
      setIsPurchasing(false);
    }
  }, [premiumStatus, refetchPremiumStatus]);

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
        {/* Premium Subscription Options */}
        {isAuthenticated && (
          <div style={{
            backgroundColor: 'white',
            borderRadius: '12px',
            overflow: 'hidden',
            marginBottom: '16px',
            border: '1px solid #E5E8EB'
          }}>
            {/* 광고 보고 7일 구독권 */}
            <button
              onClick={handleWatchAd}
              disabled={isAdLoading || premiumStatus?.subscriptionType === 'premium'}
              style={{
                width: '100%',
                padding: '16px',
                backgroundColor: 'white',
                border: 'none',
                borderBottom: '1px solid #F1F3F5',
                cursor: (isAdLoading || premiumStatus?.subscriptionType === 'premium') ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                textAlign: 'left',
                opacity: (isAdLoading || premiumStatus?.subscriptionType === 'premium') ? 0.5 : 1
              }}
            >
              <span style={{ fontSize: '24px' }}>📺</span>
              <div style={{ flex: 1 }}>
                <div style={{
                  fontSize: '15px',
                  color: '#191F28',
                  fontWeight: '500'
                }}>
                  {isAdLoading ? '광고 로딩 중...' :
                   premiumStatus?.subscriptionType === 'premium' ? '프리미엄권 이용중' :
                   premiumStatus?.subscriptionType === 'free_ad' ? '광고 구독권' :
                   '광고 보고 7일 구독권 얻기'}
                </div>
                {premiumStatus?.subscriptionType === 'free_ad' && premiumStatus?.expiresAt && (
                  <div style={{
                    fontSize: '12px',
                    color: '#8B95A1',
                    marginTop: '4px'
                  }}>
                    {Math.max(0, Math.ceil((new Date(premiumStatus.expiresAt).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)))}일 남음
                  </div>
                )}
              </div>
              {premiumStatus?.subscriptionType === 'free_ad' ? (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowCancelDialog(true);
                  }}
                  style={{
                    padding: '6px 12px',
                    fontSize: '12px',
                    color: '#E03E3E',
                    backgroundColor: 'white',
                    border: '1px solid #E03E3E',
                    borderRadius: '6px',
                    cursor: 'pointer'
                  }}
                >
                  구독 취소
                </button>
              ) : (
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path
                    d="M7.5 15L12.5 10L7.5 5"
                    stroke="#8B95A1"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
            </button>

            {/* 프리미엄 구독권 결제 */}
            <button
              onClick={handlePurchasePremium}
              disabled={isPurchasing || premiumStatus?.subscriptionType === 'premium'}
              style={{
                width: '100%',
                padding: '16px',
                backgroundColor: 'white',
                border: 'none',
                cursor: (isPurchasing || premiumStatus?.subscriptionType === 'premium') ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                textAlign: 'left',
                opacity: (isPurchasing || premiumStatus?.subscriptionType === 'premium') ? 0.5 : 1
              }}
            >
              <span style={{ fontSize: '24px' }}>🏪</span>
              <div style={{ flex: 1 }}>
                <div style={{
                  fontSize: '15px',
                  color: '#191F28',
                  fontWeight: '500'
                }}>
                  {isPurchasing ? '결제 진행 중...' :
                   premiumStatus?.subscriptionType === 'premium' ? '프리미엄 구독권' :
                   '프리미엄 구독권 구매하기'}
                </div>
                {premiumStatus?.subscriptionType === 'premium' && premiumStatus?.expiresAt && (
                  <div style={{
                    fontSize: '12px',
                    color: '#8B95A1',
                    marginTop: '4px'
                  }}>
                    {Math.max(0, Math.ceil((new Date(premiumStatus.expiresAt).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)))}일 남음
                  </div>
                )}
              </div>
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path
                  d="M7.5 15L12.5 10L7.5 5"
                  stroke="#8B95A1"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>
        )}

        {/* Search Input - 홈 화면에만 표시 */}
        {activeTab === 'home' && (
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
        )}
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
                  navigate(`/game/${game.id}`);
                }}
              >
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                  <img
                    src={game.icon}
                    alt={game.displayName}
                    style={{
                      width: '48px',
                      height: '48px',
                      borderRadius: '8px',
                      objectFit: 'cover',
                      flexShrink: 0
                    }}
                  />

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
                color: '#8B95A1',
                lineHeight: '1.6'
              }}>
                {searchQuery ? (
                  <>
                    <div style={{ fontSize: '14px', marginBottom: '8px' }}>검색 결과가 없습니다</div>
                    <div style={{ fontSize: '13px', color: '#B0B8C1' }}>
                      farmhoney1298@naver.com에<br />
                      문의하시면 원하는 게임을<br />
                      업데이트 해드려요
                    </div>
                  </>
                ) : '게임 목록을 불러오는 중...'}
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

        {activeTab === 'settings' && <SettingsScreen />}
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

      {/* 구독 취소 다이얼로그 */}
      {showCancelDialog && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '12px',
            padding: '24px',
            maxWidth: '320px',
            width: '100%'
          }}>
            <div style={{
              fontSize: '16px',
              fontWeight: 'bold',
              marginBottom: '12px',
              textAlign: 'center'
            }}>
              구독 취소
            </div>
            <div style={{
              fontSize: '14px',
              color: '#4E5968',
              marginBottom: '24px',
              textAlign: 'center',
              lineHeight: '1.5'
            }}>
              구독을 취소하시면<br />다시 광고를 보셔야해요
            </div>
            <div style={{
              display: 'flex',
              gap: '8px'
            }}>
              <button
                onClick={() => setShowCancelDialog(false)}
                style={{
                  flex: 1,
                  padding: '12px',
                  fontSize: '14px',
                  fontWeight: 'bold',
                  color: '#4E5968',
                  backgroundColor: '#F2F4F6',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer'
                }}
              >
                뒤로가기
              </button>
              <button
                onClick={handleCancelSubscription}
                style={{
                  flex: 1,
                  padding: '12px',
                  fontSize: '14px',
                  fontWeight: 'bold',
                  color: 'white',
                  backgroundColor: '#E03E3E',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer'
                }}
              >
                구독 취소
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
