'use client';

import { Inter } from 'next/font/google';
import React, { ReactNode } from 'react';
import './globals.css';
import { ThemeProvider } from '@/components/theme-provider';

const inter = Inter({ subsets: ['latin', 'cyrillic'] });

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <head>
        <title>KarmaSystem</title>
        <meta name="description" content="Система лояльности KarmaSystem" />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
      </head>
      <body className={`${inter.className} min-h-screen bg-white dark:bg-gray-900`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <div className="min-h-screen flex flex-col">
            <header className="border-b border-gray-200 dark:border-gray-800">
              <div className="container mx-auto px-4 py-4 flex justify-between items-center">
                <div className="text-xl font-bold">KarmaSystem</div>
                <nav className="flex items-center space-x-6">
                  <a href="/" className="hover:text-primary-600 dark:hover:text-primary-400">Главная</a>
                  <a href="/catalog" className="hover:text-primary-600 dark:hover:text-primary-400">Каталог</a>
                  <a href="/login" className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700">Войти</a>
                </nav>
              </div>
            </header>
            <main className="flex-1">
              {children}
            </main>
            <footer className="bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-12">
              <div className="container mx-auto px-4 py-8">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
                  <div>
                    <h3 className="font-semibold mb-4">KarmaSystem</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Система лояльности для бизнеса и клиентов
                    </p>
                  </div>
                  <div>
                    <h4 className="font-semibold mb-4">Навигация</h4>
                    <ul className="space-y-2">
                      <li><a href="/about" className="text-sm text-gray-600 hover:text-primary-600 dark:text-gray-400 dark:hover:text-primary-400">О нас</a></li>
                      <li><a href="/blog" className="text-sm text-gray-600 hover:text-primary-600 dark:text-gray-400 dark:hover:text-primary-400">Блог</a></li>
                      <li><a href="/contacts" className="text-sm text-gray-600 hover:text-primary-600 dark:text-gray-400 dark:hover:text-primary-400">Контакты</a></li>
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-semibold mb-4">Помощь</h4>
                    <ul className="space-y-2">
                      <li><a href="/faq" className="text-sm text-gray-600 hover:text-primary-600 dark:text-gray-400 dark:hover:text-primary-400">FAQ</a></li>
                      <li><a href="/support" className="text-sm text-gray-600 hover:text-primary-600 dark:text-gray-400 dark:hover:text-primary-400">Поддержка</a></li>
                      <li><a href="/privacy" className="text-sm text-gray-600 hover:text-primary-600 dark:text-gray-400 dark:hover:text-primary-400">Политика конфиденциальности</a></li>
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-semibold mb-4">Контакты</h4>
                    <ul className="space-y-2">
                      <li className="text-sm text-gray-600 dark:text-gray-400">Email: info@karmasystem.app</li>
                      <li className="text-sm text-gray-600 dark:text-gray-400">Телефон: +7 (XXX) XXX-XX-XX</li>
                    </ul>
                  </div>
                </div>
                <div className="border-t border-gray-200 dark:border-gray-700 mt-8 pt-6 text-center text-sm text-gray-500 dark:text-gray-400">
                  © {new Date().getFullYear()} KarmaSystem. Все права защищены.
                </div>
              </div>
            </footer>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
