import * as React from 'react';
import Link from 'next/link';

import { MainNav } from '@/components/navigation/main-nav';
import { MobileNav } from '@/components/navigation/mobile-nav';
import { Button } from '@/components/ui/button';
import { Icons } from '@/components/icons';

type NavItem = {
  title: string;
  href: string;
  disabled?: boolean;
};

const mainNavItems: NavItem[] = [
  {
    title: 'Главная',
    href: '/',
  },
  {
    title: 'О сервисе',
    href: '/about',
  },
  {
    title: 'Тарифы',
    href: '/pricing',
  },
  {
    title: 'Документация',
    href: '/docs',
    disabled: true,
  },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between">
        <MainNav items={mainNavItems} />
        <MobileNav items={mainNavItems} />
        <div className="flex items-center space-x-2">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/login">Войти</Link>
          </Button>
          <Button size="sm" asChild>
            <Link href="/register">Регистрация</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
