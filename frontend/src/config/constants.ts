// Базовые настройки приложения
export const APP_CONFIG = {
  name: 'KarmaSystem',
  description: 'Система лояльности KarmaSystem',
  version: '1.0.0',
} as const;

// Настройки API
export const API_CONFIG = {
  baseUrl: typeof window !== 'undefined' 
    ? (window.ENV?.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api')
    : 'http://localhost:8000/api',
  timeout: 30000, // 30 секунд
  endpoints: {
    auth: {
      login: '/auth/login',
      logout: '/auth/logout',
      refresh: '/auth/refresh',
      me: '/auth/me',
    },
    users: '/users',
    partners: '/partners',
    loyalty: {
      cards: '/loyalty/cards',
      transactions: '/loyalty/transactions',
    },
  },
} as const;

// Настройки темной/светлой темы
export const THEME_CONFIG = {
  defaultTheme: 'system',
  themes: ['light', 'dark', 'system'],
  storageKey: 'karmasystem-theme',
} as const;

// Настройки локализации
export const I18N_CONFIG = {
  defaultLocale: 'ru',
  locales: ['ru', 'en'],
  storageKey: 'karmasystem-locale',
} as const;
