"""
Модель для хранения информации об устройствах пользователей.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class UserDevice(Base):
    """
    Модель для хранения информации об устройствах пользователей,
    используемых для push-уведомлений 2FA.
    """
    __tablename__ = "user_devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Идентификатор устройства (уникальный для каждого устройства)
    device_id = Column(String(255), nullable=False, index=True)
    
    # Токен для push-уведомлений (FCM token для Android, APNS token для iOS)
    push_token = Column(String(255), nullable=True, index=True)
    
    # Информация об устройстве
    device_name = Column(String(100), nullable=True)  # Например, "iPhone 12 Pro"
    os = Column(String(50), nullable=True)           # iOS, Android, Windows, macOS, Linux
    os_version = Column(String(50), nullable=True)   # Версия ОС
    browser = Column(String(100), nullable=True)     # Chrome, Safari, Firefox и т.д.
    browser_version = Column(String(50), nullable=True)
    
    # IP-адрес последнего входа
    last_ip_address = Column(String(45), nullable=True)
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Флаги
    is_active = Column(Boolean, default=True, nullable=False)
    is_trusted = Column(Boolean, default=False, nullable=False)  # Доверенное устройство
    
    # Отношения
    user = relationship("User", back_populates="devices")
    
    def __repr__(self) -> str:
        return f"<UserDevice(id={self.id}, user_id={self.user_id}, device_name='{self.device_name}')>"
    
    @property
    def display_name(self) -> str:
        """Возвращает читаемое имя устройства."""
        if self.device_name:
            return self.device_name
        
        parts = []
        if self.os:
            parts.append(self.os)
            if self.os_version:
                parts.append(self.os_version)
        
        if self.browser:
            parts.append(self.browser)
            if self.browser_version:
                parts.append(self.browser_version)
        
        return ' '.join(parts) if parts else f"Device {self.id}"
