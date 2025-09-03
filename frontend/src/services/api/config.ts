import { API_CONFIG } from '@/config/constants';

// Базовый URL API
const API_BASE_URL = API_CONFIG.baseUrl;

// Общие заголовки для всех запросов
const DEFAULT_HEADERS = {
  'Content-Type': 'application/json',
  Accept: 'application/json',
};

// Конфигурация по умолчанию для запросов
const DEFAULT_CONFIG: RequestInit = {
  credentials: 'include',
  headers: DEFAULT_HEADERS,
};

// Типизация для ошибок API
export class ApiError extends Error {
  status: number;
  data?: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}

/**
 * Обработка ответа от сервера
 */
async function handleResponse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new ApiError(
      data.message || 'Произошла ошибка при выполнении запроса',
      response.status,
      data
    );
  }

  return data as T;
}

/**
 * Базовый метод для выполнения HTTP-запросов
 */
async function fetchApi<T>(
  endpoint: string,
  config: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...DEFAULT_CONFIG,
    ...config,
    headers: {
      ...DEFAULT_HEADERS,
      ...(config.headers || {}),
    },
  });

  return handleResponse<T>(response);
}

/**
 * GET запрос
 */
export function get<T>(endpoint: string, config: RequestInit = {}): Promise<T> {
  return fetchApi<T>(endpoint, {
    ...config,
    method: 'GET',
  });
}

/**
 * POST запрос
 */
export function post<T>(
  endpoint: string,
  data?: any,
  config: RequestInit = {}
): Promise<T> {
  return fetchApi<T>(endpoint, {
    ...config,
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  });
}

/**
 * PUT запрос
 */
export function put<T>(
  endpoint: string,
  data: any,
  config: RequestInit = {}
): Promise<T> {
  return fetchApi<T>(endpoint, {
    ...config,
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

/**
 * PATCH запрос
 */
export function patch<T>(
  endpoint: string,
  data: any,
  config: RequestInit = {}
): Promise<T> {
  return fetchApi<T>(endpoint, {
    ...config,
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * DELETE запрос
 */
export function del<T>(endpoint: string, config: RequestInit = {}): Promise<T> {
  return fetchApi<T>(endpoint, {
    ...config,
    method: 'DELETE',
  });
}

// Экспортируем все методы API
export const api = {
  get,
  post,
  put,
  patch,
  delete: del,
};
