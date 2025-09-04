"""
Сервис для отправки push-уведомлений для 2FA.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import httpx
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class PushNotificationService:
    """Сервис для работы с push-уведомлениями 2FA."""
    
    def __init__(self):
        self.base_url = "https://fcm.googleapis.com/fcm/send"
        self.server_key = "ваш_серверный_ключ_firebase"
        self.headers = {
            "Authorization": f"key={self.server_key}",
            "Content-Type": "application/json"
        }
    
    async def send_2fa_push_notification(
        self, 
        device_tokens: List[str],
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Отправка push-уведомления для подтверждения входа.
        
        Args:
            device_tokens: Список токенов устройств
            title: Заголовок уведомления
            message: Текст уведомления
            data: Дополнительные данные для уведомления
            
        Returns:
            bool: True, если уведомление успешно отправлено
        """
        if not device_tokens:
            logger.warning("No device tokens provided for push notification")
            return False
            
        payload = {
            "registration_ids": device_tokens,
            "notification": {
                "title": title,
                "body": message,
                "sound": "default",
                "click_action": "FLUTTER_NOTIFICATION_CLICK"
            },
            "data": data or {},
            "priority": "high"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Push notification sent successfully: {result}")
                    return True
                else:
                    logger.error(
                        f"Failed to send push notification: "
                        f"{response.status_code} - {response.text}"
                    )
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending push notification: {str(e)}")
            return False
    
    async def send_2fa_verification_request(
        self,
        user_id: str,
        device_tokens: List[str],
        ip_address: str,
        location: Optional[str] = None,
        device_info: Optional[str] = None
    ) -> bool:
        """
        Отправка запроса на подтверждение входа через push-уведомление.
        
        Args:
            user_id: ID пользователя
            device_tokens: Токены устройств для отправки уведомления
            ip_address: IP-адрес, с которого выполняется вход
            location: Примерное местоположение (опционально)
            device_info: Информация об устройстве (опционально)
            
        Returns:
            bool: True, если запрос успешно отправлен
        """
        title = "Требуется подтверждение входа"
        
        # Формируем информационное сообщение
        location_info = f"\nМестоположение: {location}" if location else ""
        device_info_text = f"\nУстройство: {device_info}" if device_info else ""
        
        message = (
            f"Была произведена попытка входа в ваш аккаунт.\n"
            f"IP-адрес: {ip_address}{location_info}{device_info_text}\n\n"
            "Нажмите для подтверждения входа."
        )
        
        # Дополнительные данные для обработки в приложении
        data = {
            "type": "2fa_verification",
            "user_id": user_id,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat(),
            "action_url": "yourapp://2fa/verify",
            "location": location,
            "device_info": device_info
        }
        
        return await self.send_2fa_push_notification(
            device_tokens=device_tokens,
            title=title,
            message=message,
            data=data
        )

# Создаем экземпляр сервиса для использования в приложении
push_notification_service = PushNotificationService()
