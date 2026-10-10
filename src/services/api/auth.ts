import { apiFetch } from './client';

export interface UserResponse {
  id: string;
  email: string;
  is_active: boolean;
  profile?: {
    display_name: string;
    level: number;
    xp: number;
  };
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export const authApi = {
  async register(email: string, password: string, displayName: string): Promise<AuthResponse> {
    return apiFetch<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name: displayName }),
    });
  },

  async login(email: string, password: string): Promise<AuthResponse> {
    return apiFetch<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  async logout(): Promise<void> {
    try {
      await apiFetch('/auth/logout', { method: 'POST' });
    } finally {
      localStorage.removeItem('reality_auth_token');
    }
  },

  async getCurrentUser(): Promise<UserResponse> {
    return apiFetch<UserResponse>('/auth/me');
  },
};
