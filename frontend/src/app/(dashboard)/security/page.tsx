import { auth } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'

export default async function SecurityPage() {
  const session = await auth()
  
  if (!session) {
    return null
  }

  const has2FA = session.user.twoFactorEnabled || false

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Безопасность</h1>
        <p className="mt-1 text-sm text-gray-500">
          Управление настройками безопасности и двухфакторной аутентификацией
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Двухфакторная аутентификация (2FA)</CardTitle>
          <CardDescription>
            Добавьте дополнительный уровень безопасности к своему аккаунту с помощью 2FA
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium">Двухфакторная аутентификация</h3>
              <p className="text-sm text-gray-500">
                {has2FA 
                  ? '2FA включена для вашего аккаунта.'
                  : 'Используйте приложение для аутентификации для входа в аккаунт.'
                }
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <Switch id="2fa-toggle" defaultChecked={has2FA} />
              <Label htmlFor="2fa-toggle">
                {has2FA ? 'Включено' : 'Выключено'}
              </Label>
            </div>
          </div>

          {!has2FA && (
            <div className="mt-6">
              <h4 className="font-medium mb-2">Настроить 2FA</h4>
              <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
                <li>Установите приложение для аутентификации, например Google Authenticator или Authy</li>
                <li>Отсканируйте QR-код или введите ключ вручную</li>
                <li>Введите код из приложения для подтверждения</li>
              </ol>
              <div className="mt-4">
                <Button>Настроить 2FA</Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Сеансы входа</CardTitle>
          <CardDescription>
            Управление активными сеансами входа в ваш аккаунт
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 border rounded-md">
              <div>
                <p className="font-medium">Текущая сессия</p>
                <p className="text-sm text-gray-500">
                  {new Date().toLocaleString()}
                </p>
              </div>
              <Button variant="outline" size="sm">
                Выйти из других устройств
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-red-100 bg-red-50">
        <CardHeader>
          <CardTitle className="text-red-700">Опасная зона</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <h3 className="font-medium">Удалить аккаунт</h3>
              <p className="text-sm text-red-600">
                После удаления аккаунта все ваши данные будут безвозвратно удалены.
              </p>
              <Button variant="destructive" className="mt-2">
                Удалить аккаунт
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
