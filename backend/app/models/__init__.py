"""Models package initialization.

This file ensures all models are imported so that they are registered with SQLAlchemy.
"""
from app.db.base import Base

# Import all models here to ensure they are registered with SQLAlchemy
from .user import User, Role, Permission
from .translation import InterfaceTranslation, ContentTranslation, Language, TranslationType
from .loyalty import LoyaltyAccount, LoyaltyTier, Transaction, TransactionType
from .user_login_attempt import UserLoginAttempt
from .device import UserDevice

__all__ = [
    'Base',
    'User',
    'Role',
    'Permission',
    'UserDevice',
    'InterfaceTranslation',
    'ContentTranslation',
    'Language',
    'TranslationType',
    'LoyaltyAccount',
    'LoyaltyTier',
    'Transaction',
    'TransactionType',
]
