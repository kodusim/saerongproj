// 게임 관련 타입
export interface Game {
  id: string;
  name: string;
  displayName: string;
  icon?: string;
  categories: string[]; // ['공지사항', '업데이트', '이벤트']
}

// Django API 게임 응답 타입 (djangorestframework-camel-case가 자동 변환)
export interface GameAPIResponse {
  id: number;
  gameId: string;
  displayName: string;
  iconUrl: string;
  categories: string[];
}

export interface GamesListResponse {
  results: GameAPIResponse[];
}

// 알림 데이터 타입
export interface Notification {
  title: string;
  url: string;
  date: string;
  collectedAt: string;
}

// 게임 데이터 응답 타입 (Django API)
export interface GameDataResponse {
  subcategory: string;
  category: string;
  data: {
    [key: string]: Notification[]; // '공지사항': [...], '업데이트': [...], ...
  };
}

// 구독 타입
export interface Subscription {
  id: number;
  game: number; // Game DB ID
  gameId: string;
  gameName: string;
  category: string; // '공지사항', '업데이트', '이벤트'
  createdAt: string;
}

export interface SubscriptionsListResponse {
  results: Subscription[];
}

// 알림 피드 타입
export interface NotificationFeed {
  game: string;
  gameId: string;
  category: string;
  title: string;
  url: string;
  date: string;
  collectedAt: string;
}

// 사용자 정보 타입 (토스 로그인)
export interface UserInfo {
  userKey: number;
  name?: string;
  email?: string;
}

// 인증 관련 타입
export interface LoginResponse {
  accessToken: string;
  refreshToken: string;
  user?: UserInfo; // Django가 user 정보도 함께 반환하는 경우
}

export interface AuthState {
  user: UserInfo | null;
  accessToken: string | null;
  isAuthenticated: boolean;
}

// 프리미엄 구독 상태 타입
export interface PremiumStatus {
  isPremium: boolean;
  expiresAt: string | null;
  subscriptionType: 'free_ad' | 'premium' | null;
  maxGames: number | null; // free_ad: 1, premium: null (무제한)
  subscribedGamesCount: number;
  canSubscribeMore: boolean;
}
