import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Asset, Post, Paragraph, List, ListRow, Button } from '@toss/tds-mobile';
import { colors } from '@toss/tds-colors';
import { gameAPI, subscriptionAPI } from '../api/services';
import { useAuth } from '../hooks/useAuth';
import { Spacing } from '../components/Spacing';

export default function GameDetailPage() {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();

  // 각 카테고리별 펼침/접힘 상태
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  // 게임 데이터 조회
  const { data: gameData, isLoading } = useQuery({
    queryKey: ['gameData', gameId],
    queryFn: () => gameAPI.getGameData(gameId!),
    enabled: !!gameId,
  });

  // 프리미엄 구독 상태 조회
  const { data: premiumStatus } = useQuery({
    queryKey: ['premiumStatus'],
    queryFn: subscriptionAPI.getPremiumStatus,
    enabled: isAuthenticated,
  });

  // 내 구독 목록 조회
  const { data: mySubscriptions = [] } = useQuery({
    queryKey: ['mySubscriptions'],
    queryFn: subscriptionAPI.getMySubscriptions,
    enabled: isAuthenticated,
  });

  const toggleExpand = (category: string) => {
    setExpandedCategories((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(category)) {
        newSet.delete(category);
      } else {
        newSet.add(category);
      }
      return newSet;
    });
  };

  // 현재 게임의 구독 정보
  const currentGameSubscriptions = mySubscriptions.filter(sub => sub.gameId === gameId);
  const subscribedCategories = new Set(currentGameSubscriptions.map(sub => sub.category));

  // 다른 게임 구독 여부 체크
  const otherGameSubscriptions = mySubscriptions.filter(sub => sub.gameId !== gameId);
  const hasOtherGameSubscription = otherGameSubscriptions.length > 0;
  const otherGameName = hasOtherGameSubscription ? otherGameSubscriptions[0].gameName : '';

  // 단일 카테고리 구독
  const subscribeMutation = useMutation({
    mutationFn: async (category: string) => {
      return subscriptionAPI.subscribe(gameId!, category);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mySubscriptions'] });
      alert('알림 받기가 완료되었습니다!');
    },
    onError: (error) => {
      console.error('Subscribe failed:', error);
      alert('알림 받기에 실패했습니다. 다시 시도해주세요.');
    },
  });

  // 단일 카테고리 구독 취소
  const unsubscribeMutation = useMutation({
    mutationFn: async (subscriptionId: number) => {
      return subscriptionAPI.unsubscribe(subscriptionId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mySubscriptions'] });
      alert('알림이 취소되었습니다.');
    },
    onError: (error) => {
      console.error('Unsubscribe failed:', error);
      alert('알림 취소에 실패했습니다. 다시 시도해주세요.');
    },
  });

  // 모든 소식 알림 받기
  const subscribeAllMutation = useMutation({
    mutationFn: async (categories: string[]) => {
      const promises = categories.map((category) =>
        subscriptionAPI.subscribe(gameId!, category)
      );
      return Promise.all(promises);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mySubscriptions'] });
      alert('모든 소식 알림 받기가 완료되었습니다!');
    },
    onError: (error) => {
      console.error('Subscribe all failed:', error);
      alert('알림 받기에 실패했습니다. 다시 시도해주세요.');
    },
  });

  // 카테고리 알림 받기 버튼 클릭
  const handleSubscribeCategory = (category: string) => {
    if (!isAuthenticated) {
      alert('로그인이 필요합니다.');
      return;
    }

    // 프리미엄 구독 체크
    if (!premiumStatus?.isPremium) {
      alert('구독하려면 프리미엄 구독권이 필요합니다.\n\n홈 화면에서 광고를 보거나 구독권을 구매해주세요.');
      return;
    }

    // 무료 광고 구독권 (free_ad) 사용자는 1개 게임만 가능
    if (premiumStatus.subscriptionType === 'free_ad') {
      // 다른 게임 구독 중이면 차단
      if (hasOtherGameSubscription) {
        alert(`${otherGameName} 알림 받기가 되어 있어 불가능해요.\n프리미엄 구독권을 이용해주세요.`);
        return;
      }
    }

    subscribeMutation.mutate(category);
  };

  // 카테고리 알림 취소 버튼 클릭
  const handleUnsubscribeCategory = (category: string) => {
    const subscription = currentGameSubscriptions.find(sub => sub.category === category);
    if (!subscription) return;

    if (window.confirm(`${category} 알림을 취소하시겠습니까?`)) {
      unsubscribeMutation.mutate(subscription.id);
    }
  };

  // 모든 소식 알림 받기 버튼 클릭
  const handleSubscribeAll = () => {
    if (!isAuthenticated) {
      alert('로그인이 필요합니다.');
      return;
    }

    // 프리미엄 구독 체크
    if (!premiumStatus?.isPremium) {
      alert('구독하려면 프리미엄 구독권이 필요합니다.\n\n홈 화면에서 광고를 보거나 구독권을 구매해주세요.');
      return;
    }

    // 무료 광고 구독권 (free_ad) 사용자는 1개 게임만 가능
    if (premiumStatus.subscriptionType === 'free_ad') {
      if (hasOtherGameSubscription) {
        alert(`${otherGameName} 알림 받기가 되어 있어 불가능해요.\n프리미엄 구독권을 이용해주세요.`);
        return;
      }
    }

    // 아직 구독하지 않은 카테고리만 필터링
    const categories = Object.keys(gameData?.data || {});
    const unsubscribedCategories = categories.filter(cat => !subscribedCategories.has(cat));

    if (unsubscribedCategories.length === 0) {
      alert('이미 모든 소식을 구독 중입니다.');
      return;
    }

    subscribeAllMutation.mutate(unsubscribedCategories);
  };

  const styles = {
    container: {
      minHeight: '100vh',
      paddingBottom: '120px',
      backgroundColor: colors.white,
    },
    header: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '16px 20px',
      backgroundColor: colors.white,
      borderBottom: `1px solid ${colors.grey100}`,
    },
    headerTitle: {
      fontSize: '18px',
      fontWeight: 600,
      color: colors.grey900,
    },
    content: {
      padding: '20px',
    },
    categoryHeader: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: '12px',
    },
    categoryLeft: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
    },
    categoryTitle: {
      fontSize: '16px',
      fontWeight: 'bold',
      color: colors.grey900,
    },
    categoryCount: {
      fontSize: '14px',
      color: colors.grey600,
    },
    subscribeButton: {
      padding: '6px 12px',
      fontSize: '12px',
      fontWeight: 'bold',
      border: 'none',
      borderRadius: '6px',
      cursor: 'pointer',
    },
    moreButton: {
      width: '100%',
      padding: '8px',
      marginTop: '8px',
      backgroundColor: 'transparent',
      border: `1px solid ${colors.grey200}`,
      borderRadius: '6px',
      fontSize: '13px',
      color: colors.grey700,
      cursor: 'pointer',
    },
    bottomCTA: {
      position: 'fixed' as const,
      bottom: 0,
      left: 0,
      right: 0,
      padding: '20px',
      backgroundColor: colors.white,
      borderTop: `1px solid ${colors.grey100}`,
    },
  };

  if (isLoading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p style={{ color: colors.grey600 }}>로딩 중...</p>
      </div>
    );
  }

  if (!gameData) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p style={{ color: colors.grey600 }}>게임을 찾을 수 없습니다.</p>
      </div>
    );
  }

  const categories = Object.keys(gameData.data);
  const allSubscribed = categories.every(cat => subscribedCategories.has(cat));

  return (
    <div style={styles.container}>
      {/* 헤더 */}
      <header style={styles.header}>
        <button
          onClick={() => navigate('/home')}
          style={{
            backgroundColor: 'transparent',
            border: 'none',
            padding: '4px',
            cursor: 'pointer',
          }}
        >
          <Asset.Icon
            frameShape={Asset.frameShape.CleanW24}
            backgroundColor="transparent"
            name="icon-arrow-back-ios-mono"
            color={colors.grey900}
            aria-hidden={true}
          />
        </button>
        <h1 style={styles.headerTitle}>{gameData.subcategory}</h1>
        <div style={{ width: '24px' }}></div>
      </header>

      {/* 콘텐츠 */}
      <div style={styles.content}>
        {categories.map((category) => {
          const items = gameData.data[category] || [];
          const isExpanded = expandedCategories.has(category);
          const isSubscribed = subscribedCategories.has(category);
          const displayItems = isExpanded ? items : items.slice(0, 3);

          return (
            <div key={category} style={{ marginBottom: '24px' }}>
              {/* 카테고리 헤더 */}
              <div style={styles.categoryHeader}>
                <div style={styles.categoryLeft}>
                  <span style={styles.categoryTitle}>
                    {category === '공지사항' ? '📢' : category === '이벤트' ? '🎉' : '🔧'} {category}
                  </span>
                  <span style={styles.categoryCount}>({items.length})</span>
                </div>
                {isSubscribed ? (
                  <button
                    onClick={() => handleUnsubscribeCategory(category)}
                    style={{
                      ...styles.subscribeButton,
                      color: '#E03E3E',
                      backgroundColor: 'white',
                      border: '1px solid #E03E3E',
                    }}
                  >
                    알림 중
                  </button>
                ) : (
                  <button
                    onClick={() => handleSubscribeCategory(category)}
                    style={{
                      ...styles.subscribeButton,
                      color: 'white',
                      backgroundColor: '#3182F6',
                    }}
                    disabled={subscribeMutation.isPending}
                  >
                    알림 받기
                  </button>
                )}
              </div>

              {/* 아이템 리스트 */}
              {displayItems.length > 0 && (
                <List>
                  {displayItems.map((item, index) => (
                    <ListRow
                      key={index}
                      onClick={() => window.open(item.url, '_blank')}
                      contents={
                        <ListRow.Texts
                          type="2RowTypeA"
                          top={item.title}
                          topProps={{ color: colors.grey700, fontWeight: 'bold' }}
                          bottom={new Date(item.date).toLocaleDateString()}
                          bottomProps={{ color: colors.grey600 }}
                        />
                      }
                      verticalPadding="large"
                    />
                  ))}
                </List>
              )}

              {/* 더보기 버튼 */}
              {items.length > 3 && (
                <button
                  onClick={() => toggleExpand(category)}
                  style={styles.moreButton}
                >
                  {isExpanded ? '접기 ▲' : `더보기 ▼ (${items.length - 3}개 더)`}
                </button>
              )}

              <Spacing size={16} />
            </div>
          );
        })}
      </div>

      {/* 하단 고정 버튼 */}
      <div style={styles.bottomCTA}>
        {/* 프리미엄 상태 표시 */}
        {isAuthenticated && premiumStatus && (
          <div style={{
            marginBottom: '12px',
            padding: '12px',
            backgroundColor: premiumStatus.isPremium ? '#F0F9FF' : '#FFF0F0',
            borderRadius: '8px',
            fontSize: '13px',
            textAlign: 'center',
            color: premiumStatus.isPremium ? '#1E40AF' : '#DC2626'
          }}>
            {premiumStatus.isPremium ? (
              <>
                <strong>{premiumStatus.subscriptionType === 'free_ad' ? '광고 구독권' : '프리미엄 구독권'}</strong> 사용 중
                <div style={{ fontSize: '12px', marginTop: '4px', color: '#6B7280' }}>
                  {premiumStatus.expiresAt && `${new Date(premiumStatus.expiresAt).toLocaleDateString()} 까지`}
                  {premiumStatus.subscriptionType === 'free_ad' && ' (1개 게임 구독 가능)'}
                </div>
              </>
            ) : (
              <>구독권이 없습니다. 홈에서 구독권을 받아주세요.</>
            )}
          </div>
        )}
        <Button
          color="primary"
          variant="fill"
          size="large"
          display="block"
          onClick={handleSubscribeAll}
          disabled={!premiumStatus?.isPremium || allSubscribed || subscribeAllMutation.isPending}
        >
          {allSubscribed ? '모든 소식 알림 받는 중' : '모든 소식 알림 받기'}
        </Button>
      </div>
    </div>
  );
}
