/**
 * Обрезает строку до указанной длины и добавляет многоточие, если необходимо
 * @param str - Входная строка
 * @param maxLength - Максимальная длина строки
 * @returns Обрезанная строка с многоточием, если необходимо
 */
export function truncate(str: string, maxLength: number): string {
  if (!str || str.length <= maxLength) return str;
  return `${str.substring(0, maxLength)}...`;
}

/**
 * Преобразует строку в формат kebab-case
 * @param str - Входная строка
 * @returns Строка в формате kebab-case
 */
export function toKebabCase(str: string): string {
  return str
    .replace(/([a-z])([A-Z])/g, '$1-$2')
    .replace(/[\s_]+/g, '-')
    .toLowerCase();
}

/**
 * Преобразует строку в формат CamelCase
 * @param str - Входная строка
 * @returns Строка в формате CamelCase
 */
export function toCamelCase(str: string): string {
  return str
    .replace(/(?:^\w|[A-Z]|\b\w)/g, (word, index) => {
      return index === 0 ? word.toLowerCase() : word.toUpperCase();
    })
    .replace(/[\s-]+/g, '');
}

/**
 * Преобразует строку в формат Title Case
 * @param str - Входная строка
 * @returns Строка в формате Title Case
 */
export function toTitleCase(str: string): string {
  return str
    .replace(/([A-Z])/g, ' $1')
    .replace(/^\w/, (c) => c.toUpperCase())
    .trim();
}

/**
 * Форматирует номер телефона в читаемый формат
 * @param phone - Номер телефона в любом формате
 * @returns Отформатированный номер телефона
 */
export function formatPhoneNumber(phone: string): string {
  // Удаляем все нецифровые символы
  const cleaned = ('' + phone).replace(/\D/g, '');
  
  // Проверяем, что номер начинается с 7 или 8 (российский формат)
  const match = cleaned.match(/^(7|8)?(\d{3})(\d{3})(\d{2})(\d{2})$/);
  
  if (match) {
    // Формат: +7 (XXX) XXX-XX-XX
    return `+7 (${match[2]}) ${match[3]}-${match[4]}-${match[5]}`;
  }
  
  // Если не удалось отформатировать, возвращаем исходную строку
  return phone;
}

/**
 * Проверяет, является ли строка валидным email
 * @param email - Email для проверки
 * @returns true, если email валидный, иначе false
 */
export function isValidEmail(email: string): boolean {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
}
