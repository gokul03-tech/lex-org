import { create } from 'zustand';
import apiClient from '@/lib/api';

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string, role: string) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('access_token'),
  isAuthenticated: !!localStorage.getItem('access_token'),

  login: async (email: string, password: string) => {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    const res = await apiClient.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    const { access_token, refresh_token } = res.data;
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    set({ token: access_token, isAuthenticated: true });
  },

  register: async (email, password, fullName, role) => {
    await apiClient.post('/auth/register', {
      email,
      password,
      full_name: fullName,
      role,
    });
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ user: null, token: null, isAuthenticated: false });
  },

  loadUser: async () => {
    try {
      const res = await apiClient.get('/auth/me');
      set({ user: res.data });
    } catch {
      set({ user: null, isAuthenticated: false });
    }
  },
}));
