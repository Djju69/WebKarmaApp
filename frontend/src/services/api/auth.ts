import { API_CONFIG } from '@/config/constants';
import { api } from './config';

// Типы для данных аутентификации
export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: {
    id: string;
    email: string;
    name: string;
    role: 'user' | 'partner' | 'admin';
    avatar?: string;
  };
}

/**
 * Вход в систему
 */
export async function login(credentials: LoginCredentials): Promise<AuthResponse> {
  return api.post<AuthResponse>(API_CONFIG.endpoints.auth.login, credentials);
}

/**
 * Выход из системы
 */
export async function logout(): Promise<void> {
  return api.post(API_CONFIG.endpoints.auth.logout);
}

/**
 * Обновление access токена
 */
export async function refreshToken(refreshToken: string): Promise<{ access_token: string }> {
  return api.post(API_CONFIG.endpoints.auth.refresh, { refresh_token: refreshToken });
}

/**
 * Получение информации о текущем пользователе
 */
export async function getCurrentUser(): Promise<AuthResponse['user']> {
  const response = await api.get<{ user: AuthResponse['user'] }>(API_CONFIG.endpoints.auth.me);
  return response.user;
}

/**
 * Проверка, авторизован ли пользователь
 */
export async function isAuthenticated(): Promise<boolean> {
  try {
    await getCurrentUser();
    return true;
  } catch (error) {
    return false;
  }
}

// Экспортируем все методы аутентификации
export const authApi = {
  login,
  logout,
  refreshToken,
  getCurrentUser,
  isAuthenticated,
};
