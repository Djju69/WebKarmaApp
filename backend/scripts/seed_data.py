"""
Скрипт для заполнения базы данных начальными данными.
"""
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.base import Base, engine, SessionLocal
from app.models.translation import Language, TranslationType
from app.models.user import Role, Permission, User

def create_initial_data(db: Session):
    """Создание начальных данных в базе."""
    # Создаем языки
    languages = [
        Language(code='ru', name='Русский', is_active=True, is_default=True, sort_order=1),
        Language(code='en', name='English', is_active=True, sort_order=2),
        Language(code='es', name='Español', is_active=True, sort_order=3),
        Language(code='fr', name='Français', is_active=True, sort_order=4),
    ]
    
    # Создаем роли
    roles = [
        Role(name='admin', description='Администратор системы'),
        Role(name='moderator', description='Модератор контента'),
        Role(name='user', description='Обычный пользователь'),
    ]
    
    # Создаем разрешения
    permissions = [
        Permission(name='manage_users', description='Управление пользователями', module='users'),
        Permission(name='manage_roles', description='Управление ролями', module='roles'),
        Permission(name='manage_content', description='Управление контентом', module='content'),
        Permission(name='view_analytics', description='Просмотр аналитики', module='analytics'),
    ]
    
    # Добавляем все сущности в сессию
    db.add_all(languages + roles + permissions)
    db.commit()  # Фиксируем, чтобы получить ID
    
    # Обновляем роли с разрешениями после коммита
    admin_role = db.query(Role).filter(Role.name == 'admin').first()
    moderator_role = db.query(Role).filter(Role.name == 'moderator').first()
    
    # Получаем все разрешения
    all_permissions = db.query(Permission).all()
    content_permissions = [p for p in all_permissions if p.name in ['manage_content', 'view_analytics']]
    
    # Назначаем разрешения ролям
    admin_role.permissions = all_permissions
    moderator_role.permissions = content_permissions
    
    # Создаем тестового администратора
    admin_user = User(
        username='admin',
        email='admin@example.com',
        hashed_password='$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',  # password: secret
        is_active=True,
        is_verified=True,
        preferred_language='ru'
    )
    admin_user.roles = [admin_role]  # Назначаем роль администратора
    
    # Добавляем все в сессию
    db.add_all(languages + roles + permissions + [admin_user])
    db.commit()

def main():
    print("Создание таблиц...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("Заполнение начальными данными...")
        create_initial_data(db)
        print("Готово! Созданы начальные данные.")
    except Exception as e:
        print(f"Ошибка при заполнении данных: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
