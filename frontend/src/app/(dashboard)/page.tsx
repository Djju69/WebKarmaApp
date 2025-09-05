import { Card } from '@/components/ui/card'
import { auth } from '@/lib/auth'

export default async function DashboardPage() {
  const session = await auth()
  
  if (!session) {
    return null
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Личный кабинет</h1>
        <p className="mt-1 text-sm text-gray-500">
          Добро пожаловать, {session.user.name}! Здесь вы можете управлять своим аккаунтом.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Card className="p-6">
          <h3 className="font-medium text-gray-900">Профиль</h3>
          <p className="mt-2 text-sm text-gray-500">
            Управляйте личной информацией и настройками профиля
          </p>
        </Card>

        <Card className="p-6">
          <h3 className="font-medium text-gray-900">Безопасность</h3>
          <p className="mt-2 text-sm text-gray-500">
            Настройки безопасности и двухфакторной аутентификации
          </p>
        </Card>

        <Card className="p-6">
          <h3 className="font-medium text-gray-900">Уведомления</h3>
          <p className="mt-2 text-sm text-gray-500">
            Управление уведомлениями и настройками оповещений
          </p>
        </Card>
      </div>
    </div>
  )
}
