"""
Скрипт для проверки данных в базе.
"""
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from app.models.user import User, Role, Permission

def check_data():
    """Проверяем данные в базе."""
    db = SessionLocal()
    try:
        # Проверяем пользователей
        print("\nПользователи:")
        users = db.query(User).all()
        for user in users:
            print(f"- {user.username} ({user.email}): {[r.name for r in user.roles]}")
        
        # Проверяем роли и разрешения
        print("\nРоли и разрешения:")
        roles = db.query(Role).all()
        for role in roles:
            print(f"\nРоль: {role.name}")
            print("Разрешения:")
            for perm in role.permissions:
                print(f"  - {perm.name} ({perm.module}): {perm.description}")
                
    finally:
        db.close()

if __name__ == "__main__":
    check_data()
