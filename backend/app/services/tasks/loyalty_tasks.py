"""
Background tasks for loyalty program notifications and maintenance.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.db.session import SessionLocal
from app.models.user import User
from app.models.loyalty import LoyaltyAccount, LoyaltyTier, Transaction
from app.services.notifications.loyalty_notifier import (
    get_loyalty_notifier,
    NotificationType
)
from app.core.config import settings

logger = logging.getLogger(__name__)

class LoyaltyTasks:
    """Background tasks for loyalty program operations."""
    
    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
    
    async def check_birthdays(self) -> None:
        """Check for user birthdays and send greetings with bonuses if applicable."""
        try:
            today = datetime.now().date()
            
            # Find users with birthday today
            users = self.db.query(User).filter(
                User.birth_date.isnot(None),
                User.birth_date.month == today.month,
                User.birth_date.day == today.day,
                User.is_active == True
            ).all()
            
            if not users:
                logger.info("No birthdays found for today")
                return
                
            logger.info(f"Found {len(users)} users with birthday today")
            
            notifier = get_loyalty_notifier(self.db)
            
            for user in users:
                try:
                    # Check if we already sent a birthday greeting today
                    last_notification = (
                        self.db.query(Transaction)
                        .filter(
                            Transaction.user_id == user.id,
                            Transaction.description.like('Бонус за день рождения%'),
                            Transaction.created_at >= datetime.combine(today, datetime.min.time())
                        )
                        .first()
                    )
                    
                    if not last_notification:
                        await notifier.notify_birthday_greeting(user.id)
                        logger.info(f"Sent birthday greeting to user {user.id}")
                    else:
                        logger.info(f"Birthday greeting already sent to user {user.id} today")
                        
                except Exception as e:
                    logger.error(f"Error processing birthday for user {user.id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in birthday check task: {e}")
    
    async def check_expiring_points(self, days_before: int = 7) -> None:
        """Check for points that will expire soon and notify users."""
        try:
            if not settings.POINTS_EXPIRY_DAYS:
                logger.info("Points expiration is disabled in settings")
                return
                
            expiry_date = datetime.now().date() + timedelta(days=days_before)
            expiry_start = datetime.combine(expiry_date, datetime.min.time())
            expiry_end = datetime.combine(expiry_date, datetime.max.time())
            
            # Find transactions with points that will expire on the target date
            transactions = (
                self.db.query(Transaction)
                .join(User, Transaction.user_id == User.id)
                .filter(
                    Transaction.points_expire_at.between(expiry_start, expiry_end),
                    Transaction.points > 0,
                    User.is_active == True
                )
                .all()
            )
            
            if not transactions:
                logger.info(f"No points expiring on {expiry_date}")
                return
                
            logger.info(f"Found {len(transactions)} transactions with points expiring on {expiry_date}")
            
            # Group transactions by user
            user_transactions: Dict[int, List[Transaction]] = {}
            for tx in transactions:
                if tx.user_id not in user_transactions:
                    user_transactions[tx.user_id] = []
                user_transactions[tx.user_id].append(tx)
            
            notifier = get_loyalty_notifier(self.db)
            
            for user_id, txs in user_transactions.items():
                try:
                    # Calculate total points expiring
                    total_points = sum(tx.points for tx in txs)
                    
                    # Get the earliest expiry date
                    expiry_date = min(tx.points_expire_at for tx in txs)
                    
                    # Send notification
                    await notifier.notify_points_expiry_warning(
                        user_id=user_id,
                        points=total_points,
                        expiry_date=expiry_date
                    )
                    
                    logger.info(f"Sent expiry warning to user {user_id} for {total_points} points")
                    
                except Exception as e:
                    logger.error(f"Error processing expiry notification for user {user_id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in expiring points check task: {e}")
    
    async def check_inactive_users(self, days_inactive: int = 30) -> None:
        """Check for inactive users and send them a reactivation offer."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_inactive)
            
            # Find users who haven't had any activity in the specified period
            inactive_users = (
                self.db.query(User)
                .outerjoin(Transaction, User.id == Transaction.user_id)
                .group_by(User.id)
                .having(
                    or_(
                        func.max(Transaction.created_at) < cutoff_date,
                        func.max(Transaction.created_at).is_(None)
                    )
                )
                .filter(
                    User.is_active == True,
                    User.created_at < cutoff_date  # Only users who registered long enough ago
                )
                .all()
            )
            
            if not inactive_users:
                logger.info("No inactive users found")
                return
                
            logger.info(f"Found {len(inactive_users)} inactive users")
            
            notifier = get_loyalty_notifier(self.db)
            
            for user in inactive_users:
                try:
                    # Check if we already sent a reactivation offer recently
                    last_offer = (
                        self.db.query(Transaction)
                        .filter(
                            Transaction.user_id == user.id,
                            Transaction.description.like('Специальное предложение%'),
                            Transaction.created_at >= datetime.now() - timedelta(days=7)
                        )
                        .first()
                    )
                    
                    if not last_offer:
                        # Send reactivation offer
                        await notifier.send_special_offer(
                            user_id=user.id,
                            title="Мы скучаем по вам! 💝",
                            description=(
                                f"{user.first_name or 'Дорогой клиент'}, мы заметили, что вы давно не заходили к нам!\n\n"
                                "Вернитесь и получите специальный бонус на ваш счёт!"
                            ),
                            button_text="Вернуться в магазин",
                            button_url=settings.STORE_URL
                        )
                        logger.info(f"Sent reactivation offer to user {user.id}")
                    else:
                        logger.info(f"Reactivation offer already sent to user {user.id} recently")
                        
                except Exception as e:
                    logger.error(f"Error sending reactivation offer to user {user.id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in inactive users check task: {e}")
    
    async def process_all_tasks(self) -> None:
        """Run all loyalty tasks."""
        logger.info("Starting loyalty tasks...")
        
        # Run tasks in parallel
        await asyncio.gather(
            self.check_birthdays(),
            self.check_expiring_points(),
            self.check_inactive_users(),
            return_exceptions=True
        )
        
        logger.info("All loyalty tasks completed")

def run_loyalty_tasks():
    """Run loyalty tasks in a background thread."""
    db = SessionLocal()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        tasks = LoyaltyTasks(db)
        loop.run_until_complete(tasks.process_all_tasks())
        
    except Exception as e:
        logger.error(f"Error running loyalty tasks: {e}")
    finally:
        db.close()
        loop.close()
