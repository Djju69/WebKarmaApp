/**
 * Валидация email
 * @param email - Email для валидации
 * @returns {boolean} - Валиден ли email
 */
export const validateEmail = (email: string): boolean => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
};

/**
 * Валидация номера телефона
 * @param phone - Номер телефона для валидации
 * @returns {boolean} - Валиден ли номер телефона
 */
export const validatePhone = (phone: string): boolean => {
  const re = /^\+?[0-9\s-()]{10,}$/;
  return re.test(phone);
};

/**
 * Валидация пароля
 * @param password - Пароль для валидации
 * @returns {string | null} - Сообщение об ошибке или null, если валидация пройдена
 */
export const validatePassword = (password: string): string | null => {
  if (password.length < 8) {
    return 'Пароль должен содержать минимум 8 символов';
  }
  if (!/[A-Z]/.test(password)) {
    return 'Пароль должен содержать хотя бы одну заглавную букву';
  }
  if (!/[0-9]/.test(password)) {
    return 'Пароль должен содержать хотя бы одну цифру';
  }
  return null;
};

/**
 * Валидация обязательного поля
 * @param value - Значение для проверки
 * @param fieldName - Название поля для сообщения об ошибке
 * @returns {string | null} - Сообщение об ошибке или null, если валидация пройдена
 */
export const required = (value: string, fieldName: string): string | null => {
  if (!value || value.trim() === '') {
    return `Поле "${fieldName}" обязательно для заполнения`;
  }
  return null;
};

/**
 * Валидация минимальной длины строки
 * @param value - Значение для проверки
 * @param min - Минимальная длина
 * @param fieldName - Название поля для сообщения об ошибке
 * @returns {string | null} - Сообщение об ошибке или null, если валидация пройдена
 */
export const minLength = (
  value: string,
  min: number,
  fieldName: string
): string | null => {
  if (value.length < min) {
    return `Поле "${fieldName}" должно содержать минимум ${min} символов`;
  }
  return null;
};

/**
 * Валидация максимальной длины строки
 * @param value - Значение для проверки
 * @param max - Максимальная длина
 * @param fieldName - Название поля для сообщения об ошибке
 * @returns {string | null} - Сообщение об ошибке или null, если валидация пройдена
 */
export const maxLength = (
  value: string,
  max: number,
  fieldName: string
): string | null => {
  if (value.length > max) {
    return `Поле "${fieldName}" должно содержать не более ${max} символов`;
  }
  return null;
};

/**
 * Валидация совпадения двух значений
 * @param value1 - Первое значение
 * @param value2 - Второе значение
 * @param fieldName1 - Название первого поля
 * @param fieldName2 - Название второго поля
 * @returns {string | null} - Сообщение об ошибке или null, если значения совпадают
 */
export const match = (
  value1: string,
  value2: string,
  fieldName1: string,
  fieldName2: string
): string | null => {
  if (value1 !== value2) {
    return `Поля "${fieldName1}" и "${fieldName2}" не совпадают`;
  }
  return null;
};

/**
 * Валидация числового значения
 * @param value - Значение для проверки
 * @param fieldName - Название поля для сообщения об ошибке
 * @returns {string | null} - Сообщение об ошибке или null, если валидация пройдена
 */
export const isNumber = (value: string, fieldName: string): string | null => {
  if (isNaN(Number(value))) {
    return `Поле "${fieldName}" должно быть числом`;
  }
  return null;
};

/**
 * Валидация минимального значения числа
 * @param value - Значение для проверки
 * @param min - Минимальное значение
 * @param fieldName - Название поля для сообщения об ошибке
 * @returns {string | null} - Сообщение об ошибке или null, если валидация пройдена
 */
export const minValue = (
  value: string | number,
  min: number,
  fieldName: string
): string | null => {
  const numValue = typeof value === 'string' ? Number(value) : value;
  if (numValue < min) {
    return `Значение поля "${fieldName}" должно быть не менее ${min}`;
  }
  return null;
};

/**
 * Валидация максимального значения числа
 * @param value - Значение для проверки
 * @param max - Максимальное значение
 * @param fieldName - Название поля для сообщения об ошибке
 * @returns {string | null} - Сообщение об ошибке или null, если валидация пройдена
 */
export const maxValue = (
  value: string | number,
  max: number,
  fieldName: string
): string | null => {
  const numValue = typeof value === 'string' ? Number(value) : value;
  if (numValue > max) {
    return `Значение поля "${fieldName}" должно быть не более ${max}`;
  }
  return null;
};
