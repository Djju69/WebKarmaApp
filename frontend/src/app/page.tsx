import Image from 'next/image';
import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative bg-white dark:bg-gray-900">
        <div className="container mx-auto px-4 py-16 md:py-24 lg:py-32">
          <div className="flex flex-col items-center text-center">
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-6xl">
              Система лояльности для вашего бизнеса
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-gray-600 dark:text-gray-300">
              Привлекайте новых клиентов и поощряйте постоянных с помощью современной системы лояльности KarmaSystem.
              Простая интеграция, удобное управление и рост продаж.
            </p>
            <div className="mt-10 flex items-center justify-center gap-x-6">
              <Link
                href="/register"
                className="rounded-md bg-primary-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
              >
                Начать бесплатно
              </Link>
              <Link href="/catalog" className="text-sm font-semibold leading-6 text-gray-900 dark:text-white">
                Посмотреть каталог <span aria-hidden="true">→</span>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 bg-gray-50 dark:bg-gray-800 sm:py-24">
        <div className="container mx-auto px-4">
          <div className="text-center">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-4xl">
              Почему выбирают KarmaSystem?
            </h2>
            <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-gray-600 dark:text-gray-400">
              Инновационные решения для вашего бизнеса
            </p>
          </div>
          <div className="mt-16 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
            {[
              {
                name: 'Простая интеграция',
                description: 'Быстрое подключение к вашей системе и начало работы за считанные минуты.',
                icon: '🚀',
              },
              {
                name: 'Гибкие настройки',
                description: 'Настройте программу лояльности под свои потребности и цели.',
                icon: '⚙️',
              },
              {
                name: 'Аналитика и отчеты',
                description: 'Получайте детальную аналитику по вашим клиентам и продажам.',
                icon: '📊',
              },
              {
                name: 'Мобильное приложение',
                description: 'Удобное приложение для ваших клиентов всегда под рукой.',
                icon: '📱',
              },
              {
                name: 'Круглосуточная поддержка',
                description: 'Наша команда поддержки всегда готова помочь вам в любое время.',
                icon: '🛡️',
              },
              {
                name: 'Безопасность данных',
                description: 'Мы гарантируем безопасное хранение и обработку данных ваших клиентов.',
                icon: '🔒',
              },
            ].map((feature, index) => (
              <div
                key={index}
                className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-gray-900/5 transition hover:shadow-md dark:bg-gray-800 dark:ring-white/10"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50 dark:bg-primary-900/30 text-xl">
                  {feature.icon}
                </div>
                <h3 className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">
                  {feature.name}
                </h3>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-primary-600 py-16 sm:py-24">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Готовы начать?
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-primary-100">
            Присоединяйтесь к сотням компаний, которые уже используют KarmaSystem для привлечения и удержания клиентов.
          </p>
          <div className="mt-10 flex items-center justify-center gap-x-6">
            <Link
              href="/register"
              className="rounded-md bg-white px-6 py-3 text-sm font-semibold text-primary-600 shadow-sm hover:bg-gray-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            >
              Зарегистрироваться
            </Link>
            <Link href="/contact" className="text-sm font-semibold leading-6 text-white">
              Связаться с нами <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
