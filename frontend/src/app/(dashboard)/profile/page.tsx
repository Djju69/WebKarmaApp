import { auth } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default async function ProfilePage() {
  const session = await auth()
  
  if (!session) {
    return null
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Профиль</h1>
        <p className="mt-1 text-sm text-gray-500">
          Управляйте личной информацией и настройками профиля
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Личная информация</CardTitle>
          <CardDescription>
            Обновите вашу личную информацию и контактные данные
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="name">Имя</Label>
              <Input id="name" defaultValue={session.user.name || ''} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" defaultValue={session.user.email || ''} disabled />
            </div>
          </div>
          
          <div className="pt-4">
            <Button>Сохранить изменения</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Дополнительная информация</CardTitle>
          <CardDescription>
            Дополнительные сведения о вашем аккаунте
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Дата регистрации</Label>
              <p className="text-sm text-gray-600">
                {new Date(session.user.createdAt || new Date()).toLocaleDateString()}
              </p>
            </div>
            <div className="space-y-2">
              <Label>Последний вход</Label>
              <p className="text-sm text-gray-600">
                {new Date(session.user.lastLogin || new Date()).toLocaleString()}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
