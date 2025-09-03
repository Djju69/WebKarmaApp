import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/utils/cn';

type NavItem = {
  title: string;
  href: string;
  disabled?: boolean;
};

interface MainNavProps {
  items?: NavItem[];
  className?: string;
}

export function MainNav({ items, className }: MainNavProps) {
  const pathname = usePathname();

  return (
    <nav className={cn('flex items-center space-x-4 lg:space-x-6', className)}>
      <Link href="/" className="mr-6 flex items-center space-x-2">
        <span className="font-bold">KarmaSystem</span>
      </Link>
      {items?.length ? (
        <div className="hidden md:flex items-center space-x-6">
          {items.map((item, index) =>
            item.disabled ? (
              <span
                key={index}
                className="text-muted-foreground hover:text-muted-foreground/80 cursor-not-allowed"
              >
                {item.title}
              </span>
            ) : (
              <Link
                key={index}
                href={item.href}
                className={cn(
                  'text-sm font-medium transition-colors hover:text-primary',
                  pathname === item.href
                    ? 'text-foreground'
                    : 'text-foreground/60',
                  item.disabled && 'cursor-not-allowed opacity-80'
                )}
              >
                {item.title}
              </Link>
            )
          )}
        </div>
      ) : null}
    </nav>
  );
}
