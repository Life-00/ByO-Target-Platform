import { create } from 'zustand';

export const useAuthStore = create((set) => ({
  user: null,
  isAuthenticated: false,

  setUser: (user) => {
    set({ user, isAuthenticated: !!user });
    // 로컬 스토리지에 저장 (새로고침 후에도 유지)
    if (user) {
      localStorage.setItem('user', JSON.stringify(user));
    }
  },

  clearUser: () => {
    set({ user: null, isAuthenticated: false });
    localStorage.removeItem('user');
  },

  // 앱 시작 시 로컬 스토리지에서 사용자 복원
  restoreUser: () => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        const user = JSON.parse(storedUser);
        set({ user, isAuthenticated: true });
      } catch (e) {
        localStorage.removeItem('user');
      }
    }
  },
}));
