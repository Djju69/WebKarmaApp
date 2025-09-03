/**
 * Форматирование даты в читаемый формат
 * @param date - Дата в формате строки или объекта Date
 * @param options - Настройки форматирования
 * @returns Отформатированная строка с датой
 */
export function formatDate(
  date: string | Date,
  options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }
): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat('ru-RU', options).format(dateObj);
}

/**
 * Форматирование времени в относительный формат (например, "2 часа назад")
 * @param date - Дата в формате строки или объекта Date
 * @returns Строка с относительным временем
 */
export function timeAgo(date: string | Date): string {
  const now = new Date();
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const seconds = Math.floor((now.getTime() - dateObj.getTime()) / 1000);

  const intervals = {
    год: 31536000,
    месяц: 2592000,
    неделя: 604800,
    день: 86400,
    час: 3600,
    минута: 60,
    секунда: 1,
  };

  for (const [unit, secondsInUnit] of Object.entries(intervals)) {
    const interval = Math.floor(seconds / secondsInUnit);
    if (interval >= 1) {
      if (interval === 1) {
        return `${interval} ${unit} назад`;
      } else if (interval < 5) {
        return `${interval} ${unit}а назад`;
      } else {
        return `${interval} ${unit}ов назад`;
      }
    }
  }

  return 'только что';
}

/**
 * Проверка, является ли дата сегодняшним днем
 */
export function isToday(date: Date): boolean {
  const today = new Date();
  return (
    date.getDate() === today.getDate() &&
    date.getMonth() === today.getMonth() &&
    date.getFullYear() === today.getFullYear()
  );
}
