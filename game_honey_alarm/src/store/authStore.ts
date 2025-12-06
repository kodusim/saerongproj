import { create } from 'zustand';
import type { AuthState, UserInfo } from '../types';

interface AuthStore extends AuthState {
  setUser: (user: UserInfo) => void;
  setAccessToken: (token: string) => void;
  login: (user: UserInfo, accessToken: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,

  setUser: (user) => set({ user }),

  setAccessToken: (accessToken) => set({ accessToken }),

  login: (user, accessToken) => {
    localStorage.setItem('accessToken', accessToken);
    localStorage.setItem('user', JSON.stringify(user));
    set({ user, accessToken, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('user');
    set({ user: null, accessToken: null, isAuthenticated: false });
  },
}));

// 초기화: localStorage에서 복원
const storedToken = localStorage.getItem('accessToken');
const storedUser = localStorage.getItem('user');

if (storedToken && storedUser) {
  try {
    const user = JSON.parse(storedUser);
    useAuthStore.setState({
      user,
      accessToken: storedToken,
      isAuthenticated: true,
    });
  } catch (error) {
    console.error('Failed to restore auth state:', error);
    localStorage.removeItem('accessToken');
    localStorage.removeItem('user');
  }
}
