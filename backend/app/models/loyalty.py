"""Loyalty program models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from app.db.base import Base

class LoyaltyTier(str, PyEnum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"

class LoyaltyAccount(Base):
    """Loyalty account for a user."""
    __tablename__ = "loyalty_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    points_balance = Column(Integer, default=0, nullable=False)
    tier = Column(Enum(LoyaltyTier), default=LoyaltyTier.BRONZE, nullable=False)
    total_points_earned = Column(Integer, default=0, nullable=False)
    total_points_spent = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="loyalty_accounts", lazy="selectin")
    transactions = relationship("Transaction", back_populates="loyalty_account", lazy="selectin")

    def __repr__(self):
        return f"<LoyaltyAccount user_id={self.user_id} points={self.points_balance} tier={self.tier}>"

class TransactionType(str, PyEnum):
    EARN = "earn"
    SPEND = "spend"
    ADJUSTMENT = "adjustment"
    EXPIRATION = "expiration"

class Transaction(Base):
    """Loyalty points transaction."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    loyalty_account_id = Column(Integer, ForeignKey("loyalty_accounts.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    description = Column(String(255), nullable=True)
    reference_id = Column(String(100), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="transactions", lazy="selectin")
    loyalty_account = relationship("LoyaltyAccount", back_populates="transactions", lazy="selectin")

    def __repr__(self):
        return f"<Transaction {self.id} user_id={self.user_id} type={self.transaction_type} amount={self.amount}>"
