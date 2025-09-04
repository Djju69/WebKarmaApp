"""
Loyalty service for managing points and tiers.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.loyalty import LoyaltyAccount, Transaction, LoyaltyTier, TransactionType
from app.schemas.loyalty import PointsEarn, PointsSpend, PointsAdjust, LoyaltyTier as LoyaltyTierSchema
from app.services.notifications.loyalty_notifier import get_loyalty_notifier

logger = logging.getLogger(__name__)

class LoyaltyService:
    """Service for managing loyalty program operations."""
    
    # Tier thresholds (points required for each tier)
    TIER_THRESHOLDS = {
        LoyaltyTier.BRONZE: 0,
        LoyaltyTier.SILVER: 1000,
        LoyaltyTier.GOLD: 5000,
        LoyaltyTier.PLATINUM: 15000,
    }
    
    # Points expiration in days (None means no expiration)
    POINTS_EXPIRATION_DAYS = 365  # 1 year
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_account(self, user_id: int) -> LoyaltyAccount:
        """Get or create a loyalty account for a user."""
        account = (
            self.db.query(LoyaltyAccount)
            .filter(LoyaltyAccount.user_id == user_id)
            .first()
        )
        
        if not account:
            account = LoyaltyAccount(
                user_id=user_id,
                points_balance=0,
                tier=LoyaltyTier.BRONZE,
                total_points_earned=0,
                total_points_spent=0
            )
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
            
        return account
    
    def earn_points(self, data: PointsEarn) -> Transaction:
        """Earn points for a user."""
        account = self.get_or_create_account(data.user_id)
        
        # Calculate expiration date if needed
        expires_at = None
        if self.POINTS_EXPIRATION_DAYS:
            expires_at = datetime.utcnow() + timedelta(days=self.POINTS_EXPIRATION_DAYS)
        
        # Create transaction
        transaction = Transaction(
            user_id=data.user_id,
            transaction_type=TransactionType.EARN,
            amount=data.points,
            description=data.description,
            reference_id=data.reference_id,
            points_expire_at=expires_at
        )
        
        # Update account
        old_balance = account.points_balance
        account.points_balance += data.points
        account.total_points_earned += data.points
        
        # Save changes
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        # Check for tier upgrade after commit to ensure data consistency
        old_tier = self._get_tier_info(account.tier)
        tier_upgraded = self._check_tier_upgrade(account)
        
        # Send notifications
        self._notify_points_earned(
            user_id=data.user_id,
            points=data.points,
            balance=account.points_balance,
            description=data.description,
            tier_upgraded=tier_upgraded,
            old_tier=old_tier,
            new_tier=self._get_tier_info(account.tier) if tier_upgraded else None
        )
        
        return transaction
    
    def spend_points(self, data: PointsSpend) -> Optional[Transaction]:
        """Spend points from a user's account."""
        account = self.get_or_create_account(data.user_id)
        
        # Check if user has enough points
        if account.points_balance < data.points:
            self._notify_insufficient_points(
                user_id=data.user_id,
                requested_points=data.points,
                current_balance=account.points_balance,
                description=data.description
            )
            return None
        
        # Create transaction
        transaction = Transaction(
            user_id=data.user_id,
            transaction_type=TransactionType.SPEND,
            amount=-data.points,
            description=data.description,
            reference_id=data.reference_id
        )
        
        # Update account
        old_balance = account.points_balance
        account.points_balance -= data.points
        account.total_points_spent += data.points
        
        # Save changes
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        # Send notification
        self._notify_points_spent(
            user_id=data.user_id,
            points=data.points,
            balance=account.points_balance,
            description=data.description
        )
        
        return transaction
    
    def adjust_points(self, data: PointsAdjust) -> Transaction:
        """Adjust points (admin function)."""
        account = self.get_or_create_account(data.user_id)
        
        # Determine transaction type and update account
        if data.points > 0:
            transaction_type = TransactionType.ADJUSTMENT
            account.points_balance += data.points
            account.total_points_earned += data.points
        else:
            transaction_type = TransactionType.ADJUSTMENT
            points = abs(data.points)
            account.points_balance = max(0, account.points_balance - points)
        
        # Create transaction
        transaction = Transaction(
            user_id=data.user_id,
            loyalty_account_id=account.id,
            amount=data.points,
            transaction_type=transaction_type,
            description=data.description,
            reference_id=data.reference_id
        )
        
        # Update tier if needed
        self._update_tier(account)
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        return transaction
    
    def get_account_summary(self, user_id: int) -> Dict:
        """Get a summary of the user's loyalty account."""
        account = self.get_or_create_account(user_id)
        
        # Get next tier information
        current_tier = account.tier
        next_tier = self._get_next_tier(current_tier)
        points_to_next_tier = 0
        
        if next_tier:
            points_to_next_tier = max(0, self.TIER_THRESHOLDS[next_tier] - 
                                    (account.total_points_earned - account.total_points_spent))
        
        return {
            "user_id": user_id,
            "points_balance": account.points_balance,
            "current_tier": current_tier.value,
            "next_tier": next_tier.value if next_tier else None,
            "points_to_next_tier": points_to_next_tier,
            "total_points_earned": account.total_points_earned,
            "total_points_spent": account.total_points_spent,
            "tier_benefits": self._get_tier_benefits(current_tier)
        }
    
    def _check_tier_upgrade(self, account: LoyaltyAccount) -> bool:
        """Check and update user's tier based on points."""
        current_tier = account.tier
        new_tier = self._calculate_tier(account.total_points_earned)
        
        if new_tier != current_tier:
            old_tier = self._get_tier_info(current_tier)
            account.tier = new_tier
            self.db.commit()
            
            # Send tier upgrade notification
            self._notify_tier_upgrade(
                user_id=account.user_id,
                old_tier=old_tier,
                new_tier=self._get_tier_info(new_tier)
            )
            return True
        return False
    
    def _update_tier(self, account: LoyaltyAccount) -> None:
        """Update user's tier based on points."""
        total_points = account.total_points_earned - account.total_points_spent
        
        # Determine new tier
        new_tier = LoyaltyTier.BRONZE
        for tier, threshold in sorted(self.TIER_THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
            if total_points >= threshold:
                new_tier = tier
                break
        
        # Update if tier changed
        if new_tier != account.tier:
            account.tier = new_tier
            self.db.commit()
    
    def _get_next_tier(self, current_tier: LoyaltyTier) -> Optional[LoyaltyTier]:
        """Get the next tier after the current one."""
        tiers = list(LoyaltyTier)
        current_index = tiers.index(current_tier)
        
        if current_index < len(tiers) - 1:
            return tiers[current_index + 1]
        return None
    
    def _get_tier_info(self, tier: str) -> LoyaltyTierSchema:
        """Get detailed information about a tier."""
        benefits = self._get_tier_benefits(tier)
        return LoyaltyTierSchema(
            name=tier,
            **benefits
        )
    
    def _get_tier_benefits(self, tier: str) -> Dict[str, Any]:
        """Get benefits for a given tier."""
        benefits: Dict[str, Any] = {
            "discount": 0,
            "free_shipping_threshold": None,
            "free_shipping": False,
            "birthday_bonus_multiplier": 1.0,
            "min_points": self.TIER_THRESHOLDS.get(tier, 0),
            "next_tier_threshold": None,
            "name": tier,
            "description": ""
        }
        
        # Set benefits based on tier
        if tier == LoyaltyTier.BRONZE:
            benefits.update({
                "discount": 0,
                "next_tier_threshold": self.TIER_THRESHOLDS.get(LoyaltyTier.SILVER, 0),
                "description": "Basic level with standard benefits"
            })
            
        elif tier == LoyaltyTier.SILVER:
            benefits.update({
                "discount": 5,
                "free_shipping_threshold": 5000,
                "birthday_bonus_multiplier": 1.5,
                "next_tier_threshold": self.TIER_THRESHOLDS.get(LoyaltyTier.GOLD, 0),
                "description": "5% discount and free shipping on orders over 5000"
            })
            
        elif tier == LoyaltyTier.GOLD:
            benefits.update({
                "discount": 10,
                "free_shipping_threshold": 3000,
                "birthday_bonus_multiplier": 2.0,
                "next_tier_threshold": self.TIER_THRESHOLDS.get(LoyaltyTier.PLATINUM, 0),
                "description": "10% discount and free shipping on orders over 3000"
            })
            
        elif tier == LoyaltyTier.PLATINUM:
            benefits.update({
                "discount": 15,
                "free_shipping": True,
                "birthday_bonus_multiplier": 3.0,
                "description": "15% discount and always free shipping"
            })
            
        return benefits
    
    def _get_expiring_soon_points(self, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get points that will expire soon for a user."""
        if not settings.POINTS_EXPIRY_DAYS:
            return []
            
        expiry_date = datetime.utcnow() + timedelta(days=days)
        
        expiring_points = (
            self.db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.points_expire_at <= expiry_date,
                Transaction.points_expire_at >= datetime.utcnow(),
                Transaction.transaction_type == TransactionType.EARN
            )
            .order_by(Transaction.points_expire_at)
            .all()
        )
        
        return [
            {
                "points": t.amount,
                "expires_at": t.points_expire_at.isoformat(),
                "days_until_expiry": (t.points_expire_at - datetime.utcnow()).days,
                "description": t.description or "Points expiring soon"
            }
            for t in expiring_points
        ]
