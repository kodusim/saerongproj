import apiClient from './client';
import type {
  Game,
  GameDataResponse,
  GamesListResponse,
  LoginResponse,
  NotificationFeed,
  PremiumStatus,
  Subscription,
  SubscriptionsListResponse,
  UserInfo
} from '../types';

// ===== 인증 API =====
export const authAPI = {
  // 토스 로그인 (authorizationCode 교환)
  login: async (authorizationCode: string, referrer: string): Promise<LoginResponse> => {
    const { data } = await apiClient.post('/api/auth/login', {
      authorizationCode,
      referrer,
    });
    return data;
  },

  // 사용자 정보 조회
  getUserInfo: async (): Promise<UserInfo> => {
    const { data } = await apiClient.get('/api/auth/me');
    return data;
  },

  // 토큰 갱신
  refreshToken: async (refreshToken: string): Promise<LoginResponse> => {
    const { data } = await apiClient.post('/api/auth/refresh', {
      refreshToken,
    });
    return data;
  },

  // 로그아웃
  logout: async (): Promise<void> => {
    await apiClient.post('/api/auth/logout');
  },
};

// ===== 게임 API =====
export const gameAPI = {
  // 게임 목록 조회
  getGames: async (): Promise<Game[]> => {
    try {
      const { data } = await apiClient.get<GamesListResponse>('/api/games/');

      // djangorestframework-camel-case가 자동으로 camelCase로 변환해줌
      return data.results.map((game) => ({
        id: game.gameId,
        name: game.gameId,
        displayName: game.displayName,
        icon: game.iconUrl,
        categories: game.categories,
      }));
    } catch (error) {
      // API가 없거나 에러 발생 시 기본 게임 목록 반환
      console.warn('Failed to fetch games from API, using fallback:', error);
      return [
        {
          id: 'maplestory',
          name: 'maplestory',
          displayName: '메이플스토리',
          icon: 'https://via.placeholder.com/64x64.png?text=MS',
          categories: ['공지사항', '업데이트', '이벤트'],
        },
      ];
    }
  },

  // 특정 게임 데이터 조회
  getGameData: async (gameId: string): Promise<GameDataResponse> => {
    const { data } = await apiClient.get(`/api/${gameId}/`);
    return data;
  },
};

// ===== 구독 API =====
export const subscriptionAPI = {
  // 내 구독 목록 조회
  getMySubscriptions: async (): Promise<Subscription[]> => {
    const { data } = await apiClient.get<SubscriptionsListResponse>('/api/subscriptions/');
    return data.results;
  },

  // 구독 추가
  subscribe: async (gameId: string, category: string): Promise<Subscription> => {
    const { data} = await apiClient.post<Subscription>('/api/subscriptions/', {
      gameId,  // djangorestframework-camel-case가 자동으로 game_id로 변환
      category,
    });
    return data;
  },

  // 구독 취소
  unsubscribe: async (subscriptionId: number): Promise<void> => {
    await apiClient.delete(`/api/subscriptions/${subscriptionId}/`);
  },

  // 프리미엄 구독 상태 조회
  getPremiumStatus: async (): Promise<PremiumStatus> => {
    const { data } = await apiClient.get('/api/premium/status/');
    return data;
  },

  // 프리미엄 구독권 부여 (광고 시청 또는 인앱결제)
  grantPremium: async (type: 'free_ad' | 'premium', orderId?: string): Promise<{ expiresAt: string }> => {
    const { data } = await apiClient.post('/api/premium/grant/', {
      subscriptionType: type,
      orderId,  // 인앱결제 주문 ID (결제 검증용)
    });
    return data;
  },

  // 프리미엄 구독권 취소
  cancelPremium: async (): Promise<void> => {
    await apiClient.post('/api/premium/cancel/');
  },
};

// ===== 알림 API =====
export const notificationAPI = {
  // 알림 피드 조회 (내가 구독한 게임의 최신 소식)
  getFeed: async (limit?: number): Promise<NotificationFeed[]> => {
    const { data } = await apiClient.get<NotificationFeed[]>('/api/notifications/', {
      params: { limit },
    });
    return data;
  },

  // 푸시 토큰 등록
  registerPushToken: async (token: string, deviceType: 'android' | 'ios'): Promise<void> => {
    await apiClient.post('/api/push-tokens/', {
      token,
      deviceType,  // djangorestframework-camel-case가 자동으로 device_type으로 변환
    });
  },
};

// ===== 테스트 API =====
export const testAPI = {
  // 테스트 푸시 알림 발송
  sendTestPush: async (title: string, body?: string): Promise<{ success: boolean; message: string }> => {
    const { data } = await apiClient.post('/api/test/push/', {
      title,
      body,
    });
    return data;
  },
};
