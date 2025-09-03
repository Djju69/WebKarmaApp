/**
 * Сохраняет данные в localStorage
 * @param key - Ключ для сохранения
 * @param value - Значение для сохранения (будет преобразовано в JSON)
 */
export function saveToLocalStorage<T>(key: string, value: T): void {
  if (typeof window === 'undefined') return;
  
  try {
    const serializedValue = JSON.stringify(value);
    localStorage.setItem(key, serializedValue);
  } catch (error) {
    console.error('Ошибка при сохранении в localStorage:', error);
  }
}

/**
 * Получает данные из localStorage
 * @param key - Ключ для получения данных
 * @param defaultValue - Значение по умолчанию, если данные не найдены
 * @returns Сохраненное значение или значение по умолчанию
 */
export function getFromLocalStorage<T>(key: string, defaultValue: T): T {
  if (typeof window === 'undefined') return defaultValue;
  
  try {
    const serializedValue = localStorage.getItem(key);
    if (serializedValue === null) return defaultValue;
    return JSON.parse(serializedValue) as T;
  } catch (error) {
    console.error('Ошибка при чтении из localStorage:', error);
    return defaultValue;
  }
}

/**
 * Удаляет данные из localStorage
 * @param key - Ключ для удаления
 */
export function removeFromLocalStorage(key: string): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(key);
}

/**
 * Очищает все данные из localStorage
 */
export function clearLocalStorage(): void {
  if (typeof window === 'undefined') return;
  localStorage.clear();
}

/**
 * Сохраняет данные в sessionStorage
 * @param key - Ключ для сохранения
 * @param value - Значение для сохранения (будет преобразовано в JSON)
 */
export function saveToSessionStorage<T>(key: string, value: T): void {
  if (typeof window === 'undefined') return;
  
  try {
    const serializedValue = JSON.stringify(value);
    sessionStorage.setItem(key, serializedValue);
  } catch (error) {
    console.error('Ошибка при сохранении в sessionStorage:', error);
  }
}

/**
 * Получает данные из sessionStorage
 * @param key - Ключ для получения данных
 * @param defaultValue - Значение по умолчанию, если данные не найдены
 * @returns Сохраненное значение или значение по умолчанию
 */
export function getFromSessionStorage<T>(key: string, defaultValue: T): T {
  if (typeof window === 'undefined') return defaultValue;
  
  try {
    const serializedValue = sessionStorage.getItem(key);
    if (serializedValue === null) return defaultValue;
    return JSON.parse(serializedValue) as T;
  } catch (error) {
    console.error('Ошибка при чтении из sessionStorage:', error);
    return defaultValue;
  }
}

/**
 * Удаляет данные из sessionStorage
 * @param key - Ключ для удаления
 */
export function removeFromSessionStorage(key: string): void {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(key);
}

/**
 * Очищает все данные из sessionStorage
 */
export function clearSessionStorage(): void {
  if (typeof window === 'undefined') return;
  sessionStorage.clear();
}
