import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu } from 'lucide-react';

import { cn } from '@/utils/cn';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';

type NavItem = {
  title: string;
  href: string;
  disabled?: boolean;
};

interface MobileNavProps {
  items: NavItem[];
}

export function MobileNav({ items }: MobileNavProps) {
  const [open, setOpen] = React.useState(false);
  const pathname = usePathname();

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          className="mr-2 px-0 text-base hover:bg-transparent focus:ring-0 focus:ring-offset-0 md:hidden"
        >
          <Menu className="h-6 w-6" />
          <span className="sr-only">Toggle Menu</span>
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="pr-0">
        <div className="px-7">
          <Link
            href="/"
            className="flex items-center"
            onClick={() => setOpen(false)}
          >
            <span className="font-bold">KarmaSystem</span>
          </Link>
        </div>
        <div className="mt-6 h-[calc(100vh-8rem)] overflow-y-auto px-7">
          <div className="flex flex-col space-y-3">
            {items?.map((item, index) =>
              item.disabled ? (
                <span
                  key={index}
                  className="text-muted-foreground hover:text-muted-foreground/80 flex w-full cursor-not-allowed items-center rounded-md p-2 text-sm font-medium"
                >
                  {item.title}
                </span>
              ) : (
                <Link
                  key={index}
                  href={item.href}
                  className={cn(
                    'flex w-full items-center rounded-md p-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground',
                    pathname === item.href
                      ? 'bg-accent text-accent-foreground'
                      : 'text-foreground/60',
                    item.disabled && 'cursor-not-allowed opacity-60'
                  )}
                  onClick={() => setOpen(false)}
                >
                  {item.title}
                </Link>
              )
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
