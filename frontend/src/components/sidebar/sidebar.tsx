import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { User } from 'next-auth'

const navigation = [
  { name: 'Обзор', href: '/dashboard', icon: 'dashboard' },
  { name: 'Профиль', href: '/dashboard/profile', icon: 'person' },
  { name: 'Безопасность', href: '/dashboard/security', icon: 'lock' },
  { name: 'Уведомления', href: '/dashboard/notifications', icon: 'notifications' },
  { name: 'Настройки', href: '/dashboard/settings', icon: 'settings' },
]

export function Sidebar({ user }: { user: User }) {
  const pathname = usePathname()

  return (
    <div className="hidden md:flex md:flex-shrink-0">
      <div className="flex flex-col w-64 border-r border-gray-200 bg-white">
        <div className="h-0 flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
          <div className="flex-1 px-3 space-y-1">
            {navigation.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  pathname === item.href
                    ? 'bg-gray-100 text-gray-900'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
                  'group flex items-center px-2 py-2 text-sm font-medium rounded-md'
                )}
              >
                <span className="material-icons-outlined mr-3 flex-shrink-0 h-6 w-6">
                  {item.icon}
                </span>
                {item.name}
              </Link>
            ))}
          </div>
        </div>
        <div className="flex-shrink-0 flex border-t border-gray-200 p-4">
          <div className="flex items-center">
            <div>
              <div className="text-base font-medium text-gray-800">
                {user.name}
              </div>
              <div className="text-sm font-medium text-gray-500">
                {user.email}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
