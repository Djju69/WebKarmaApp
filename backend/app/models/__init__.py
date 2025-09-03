"""Models package initialization.

This file ensures all models are imported so that they are registered with SQLAlchemy.
"""
from app.db.base import Base

# Import all models here to ensure they are registered with SQLAlchemy
from .user import User, Role, Permission
from .translation import InterfaceTranslation, ContentTranslation, Language, TranslationType
from .loyalty import LoyaltyAccount, LoyaltyTier, Transaction, TransactionType

__all__ = [
    'Base',
    'User',
    'Role',
    'Permission',
    'InterfaceTranslation',
    'ContentTranslation',
    'Language',
    'TranslationType',
    'LoyaltyAccount',
    'LoyaltyTier',
    'Transaction',
    'TransactionType',
]
