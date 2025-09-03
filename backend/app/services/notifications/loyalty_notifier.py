"""
Loyalty event notification service.
Handles sending notifications for various loyalty program events.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from sqlalchemy.orm import Session
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from app.core.config import settings
from app.models.user import User
from app.models.loyalty import LoyaltyAccount, Transaction, LoyaltyTier
from app.schemas.loyalty import LoyaltyTier as LoyaltyTierSchema

logger = logging.getLogger(__name__)

class NotificationType(str, Enum):
    """Types of loyalty notifications."""
    POINTS_EARNED = "points_earned"
    POINTS_SPENT = "points_spent"
    TIER_UPGRADED = "tier_upgraded"
    BIRTHDAY_GREETING = "birthday_greeting"
    SPECIAL_OFFER = "special_offer"
    POINTS_EXPIRY_WARNING = "points_expiry_warning"
    WELCOME_BONUS = "welcome_bonus"

class LoyaltyNotifier:
    """Handles sending loyalty-related notifications to users."""
    
    def __init__(self, db: Session, bot: Optional[Bot] = None):
        """Initialize notifier with database session and optional Telegram bot instance."""
        self.db = db
        self.bot = bot
    
    async def notify_points_earned(
        self, 
        user_id: int, 
        points: int, 
        balance: int,
        reason: Optional[str] = None
    ) -> bool:
        """Notify user about earned points."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.telegram_id:
            return False
            
        message = (
            f"🎉 *Вы получили {points} бонусных баллов!*\n\n"
            f"💳 Текущий баланс: *{balance}* баллов"
        )
        
        if reason:
            message += f"\n📝 Причина: {reason}"
            
        return await self._send_telegram_message(
            chat_id=user.telegram_id,
            text=message,
            notification_type=NotificationType.POINTS_EARNED
        )
    
    async def notify_points_spent(
        self, 
        user_id: int, 
        points: int, 
        balance: int,
        reason: Optional[str] = None
    ) -> bool:
        """Notify user about spent points."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.telegram_id:
            return False
            
        message = (
            f"💸 *Списано {points} бонусных баллов*\n\n"
            f"💳 Остаток: *{balance}* баллов"
        )
        
        if reason:
            message += f"\n📝 Причина: {reason}"
            
        return await self._send_telegram_message(
            chat_id=user.telegram_id,
            text=message,
            notification_type=NotificationType.POINTS_SPENT
        )
    
    async def notify_tier_upgrade(
        self, 
        user_id: int, 
        old_tier: LoyaltyTierSchema,
        new_tier: LoyaltyTierSchema
    ) -> bool:
        """Notify user about loyalty tier upgrade."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.telegram_id:
            return False
            
        message = (
            f"🏆 *Поздравляем!* 🎉\n\n"
            f"Вы достигли нового уровня лояльности: *{new_tier.name}*!\n\n"
            f"Ваши привилегии теперь включают:\n"
            f"• Скидка {new_tier.discount}% на все покупки\n"
        )
        
        if new_tier.free_shipping_threshold is not None:
            message += f"• Бесплатная доставка от {new_tier.free_shipping_threshold} ₽\n"
            
        if new_tier.birthday_bonus_multiplier > 1:
            message += f"• Бонус x{new_tier.birthday_bonus_multiplier} баллов в день рождения\n"
            
        message += "\nСпасибо за вашу лояльность!"
        
        return await self._send_telegram_message(
            chat_id=user.telegram_id,
            text=message,
            notification_type=NotificationType.TIER_UPGRADED
        )
    
    async def notify_birthday_greeting(self, user_id: int) -> bool:
        """Send birthday greeting to user with potential bonus."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.telegram_id:
            return False
            
        # Get user's loyalty account
        account = self.db.query(LoyaltyAccount).filter(
            LoyaltyAccount.user_id == user_id
        ).first()
        
        if not account:
            return False
            
        # Get current tier
        tier = self.db.query(LoyaltyTier).get(account.tier_id)
        if not tier:
            return False
            
        bonus_points = 0
        if tier.birthday_bonus_multiplier > 1:
            bonus_points = int(100 * tier.birthday_bonus_multiplier)
            
            # Add bonus points to account
            from app.services.loyalty.service import LoyaltyService
            loyalty_service = LoyaltyService(self.db)
            loyalty_service.earn_points({
                'user_id': user_id,
                'points': bonus_points,
                'description': f'Бонус за день рождения (уровень {tier.name})',
                'reference_id': f'birthday_{datetime.now().date().isoformat()}'
            })
        
        message = (
            f"🎂 *С Днём Рождения, {user.first_name or 'друг'}!* 🎉\n\n"
            f"Спасибо, что вы с нами! "
        )
        
        if bonus_points > 0:
            message += (
                f"В честь вашего праздника мы дарим вам *{bonus_points}* бонусных баллов!\n\n"
                f"💳 Текущий баланс: {account.points_balance + bonus_points} баллов"
            )
        else:
            message += "Желаем вам отличного дня!"
            
        return await self._send_telegram_message(
            chat_id=user.telegram_id,
            text=message,
            notification_type=NotificationType.BIRTHDAY_GREETING
        )
    
    async def notify_points_expiry_warning(
        self, 
        user_id: int, 
        points: int, 
        expiry_date: datetime
    ) -> bool:
        """Notify user about soon-to-expire points."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.telegram_id:
            return False
            
        expiry_str = expiry_date.strftime("%d.%m.%Y")
        
        message = (
            f"⚠️ *Скоро истекают бонусные баллы!*\n\n"
            f"{points} ваших бонусных баллов истекают *{expiry_str}*\n\n"
            f"Не упустите возможность использовать их!"
        )
        
        # Add button to view available rewards
        keyboard = [
            [InlineKeyboardButton("🎁 Посмотреть награды", callback_data="view_rewards")],
            [InlineKeyboardButton("🛍 Перейти в магазин", url=settings.STORE_URL)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        return await self._send_telegram_message(
            chat_id=user.telegram_id,
            text=message,
            reply_markup=reply_markup,
            notification_type=NotificationType.POINTS_EXPIRY_WARNING
        )
    
    async def send_special_offer(
        self,
        user_id: int,
        title: str,
        description: str,
        image_url: Optional[str] = None,
        button_text: Optional[str] = None,
        button_url: Optional[str] = None
    ) -> bool:
        """Send special offer to user."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.telegram_id:
            return False
            
        message = f"🎁 *{title}*\n\n{description}"
        
        reply_markup = None
        if button_text and button_url:
            keyboard = [[InlineKeyboardButton(button_text, url=button_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        return await self._send_telegram_message(
            chat_id=user.telegram_id,
            text=message,
            reply_markup=reply_markup,
            notification_type=NotificationType.SPECIAL_OFFER,
            image_url=image_url
        )
    
    async def _send_telegram_message(
        self,
        chat_id: int,
        text: str,
        notification_type: NotificationType,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        image_url: Optional[str] = None
    ) -> bool:
        """Internal method to send message via Telegram."""
        if not self.bot:
            try:
                self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
                return False
        
        try:
            # If image URL is provided, send photo with caption
            if image_url:
                await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=image_url,
                    caption=text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            
            logger.info(f"Sent {notification_type} notification to user {chat_id}")
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to send {notification_type} notification to {chat_id}: {e}"
            )
            return False

# Helper function to get notifier instance
def get_loyalty_notifier(db: Session) -> LoyaltyNotifier:
    """Get a new instance of LoyaltyNotifier with database session."""
    return LoyaltyNotifier(db)
