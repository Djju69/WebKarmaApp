""
Telegram bot command handlers for loyalty system.
"""
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services.loyalty.service import LoyaltyService
from app.core.security import get_current_user
from app.models.user import User

class LoyaltyCommandHandlers:
    """Handlers for loyalty-related Telegram commands."""
    
    def __init__(self):
        self.commands = [
            ('balance', self.show_balance),
            ('earn', self.earn_points),
            ('spend', self.spend_points),
            ('history', self.show_history),
            ('help_loyalty', self.help_loyalty)
        ]
        
        self.callbacks = {
            'loyalty_earn': self.handle_earn_callback,
            'loyalty_spend': self.handle_spend_callback,
            'loyalty_history': self.handle_history_callback
        }
    
    async def show_balance(self, update: Update, context: CallbackContext) -> None:
        """Show user's loyalty points balance and tier."""
        db = next(get_db())
        try:
            # Get user from database
            user = db.query(User).filter(
                User.telegram_id == update.effective_user.id
            ).first()
            
            if not user:
                await update.message.reply_text(
                    "❌ Вы не зарегистрированы в системе. Используйте /start для регистрации."
                )
                return
            
            # Get loyalty account info
            service = LoyaltyService(db)
            account_info = service.get_account_summary(user.id)
            
            # Format message
            message = (
                f"💎 *Ваш баланс:* {account_info['points_balance']} баллов\n"
                f"🏆 *Текущий уровень:* {account_info['tier_benefits']['name']}\n"
                f"📊 *Всего накоплено:* {account_info['total_points_earned']} баллов\n"
                f"💳 *Потрачено баллов:* {account_info['total_points_spent']}\n\n"
                f"🎁 *Бонусы уровня:*\n"
                f"- Скидка {account_info['tier_benefits']['discount']}% на все покупки\n"
            )
            
            if account_info['tier_benefits']['free_shipping_threshold'] is not None:
                message += f"- Бесплатная доставка от {account_info['tier_benefits']['free_shipping_threshold']} ₽\n"
            if account_info['next_tier']:
                message += f"\nДо следующего уровня осталось: {account_info['points_to_next_tier']} баллов"
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await update.message.reply_text(
                "❌ Произошла ошибка при получении информации о бонусах. Пожалуйста, попробуйте позже."
            )
            print(f"Error in show_balance: {e}")
        finally:
            db.close()
    
    async def earn_points(self, update: Update, context: CallbackContext) -> None:
        """Handle /earn command to add points to user's account."""
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "Использование: /earn <количество_баллов> [причина]"
            )
            return
            
        try:
            points = int(context.args[0])
            reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Начисление баллов"
            
            db = next(get_db())
            try:
                user = db.query(User).filter(
                    User.telegram_id == update.effective_user.id
                ).first()
                
                if not user:
                    await update.message.reply_text(
                        "❌ Вы не зарегистрированы в системе."
                    )
                    return
                
                # Add points using loyalty service
                service = LoyaltyService(db)
                transaction = service.earn_points({
                    'user_id': user.id,
                    'points': points,
                    'description': reason,
                    'reference_id': f'tg_{update.update_id}'
                })
                
                await update.message.reply_text(
                    f"✅ Вам начислено {points} бонусных баллов!\n"
                    f"💳 Текущий баланс: {transaction.loyalty_account.points_balance} баллов"
                )
                
            finally:
                db.close()
                
        except ValueError:
            await update.message.reply_text("Пожалуйста, укажите корректное количество баллов (целое число).")
        except Exception as e:
            await update.message.reply_text(
                "❌ Произошла ошибка при начислении баллов. Пожалуйста, попробуйте позже."
            )
            print(f"Error in earn_points: {e}")
    
    async def spend_points(self, update: Update, context: CallbackContext) -> None:
        """Handle /spend command to use points from user's account."""
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "Использование: /spend <количество_баллов> [причина]"
            )
            return
            
        try:
            points = int(context.args[0])
            reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Списание баллов"
            
            db = next(get_db())
            try:
                user = db.query(User).filter(
                    User.telegram_id == update.effective_user.id
                ).first()
                
                if not user:
                    await update.message.reply_text(
                        "❌ Вы не зарегистрированы в системе."
                    )
                    return
                
                # Spend points using loyalty service
                service = LoyaltyService(db)
                transaction = service.spend_points({
                    'user_id': user.id,
                    'points': points,
                    'description': reason,
                    'reference_id': f'tg_{update.update_id}'
                })
                
                if not transaction:
                    await update.message.reply_text(
                        "❌ Недостаточно баллов для списания."
                    )
                    return
                
                await update.message.reply_text(
                    f"✅ Списано {points} бонусных баллов.\n"
                    f"💳 Остаток: {transaction.loyalty_account.points_balance} баллов"
                )
                
            finally:
                db.close()
                
        except ValueError:
            await update.message.reply_text("Пожалуйста, укажите корректное количество баллов (целое число).")
        except Exception as e:
            await update.message.reply_text(
                "❌ Произошла ошибка при списании баллов. Пожалуйста, попробуйте позже."
            )
            print(f"Error in spend_points: {e}")
    
    async def show_history(self, update: Update, context: CallbackContext) -> None:
        """Show user's transaction history."""
        db = next(get_db())
        try:
            user = db.query(User).filter(
                User.telegram_id == update.effective_user.id
            ).first()
            
            if not user:
                await update.message.reply_text(
                    "❌ Вы не зарегистрированы в системе."
                )
                return
            
            # Get transaction history
            from app.models.loyalty import Transaction
            transactions = (
                db.query(Transaction)
                .filter(Transaction.user_id == user.id)
                .order_by(Transaction.created_at.desc())
                .limit(10)
                .all()
            )
            
            if not transactions:
                await update.message.reply_text("У вас пока нет операций с бонусами.")
                return
            
            # Format history message
            message = "*История операций:*\n\n"
            for tx in transactions:
                emoji = "⬆️" if tx.transaction_type in ["earn", "adjustment"] else "⬇️"
                date = tx.created_at.strftime("%d.%m.%Y %H:%M")
                message += f"{emoji} *{tx.amount}* баллов - {tx.description}\n"
                message += f"`{date}`\n\n"
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await update.message.reply_text(
                "❌ Не удалось загрузить историю операций. Пожалуйста, попробуйте позже."
            )
            print(f"Error in show_history: {e}")
        finally:
            db.close()
    
    async def help_loyalty(self, update: Update, context: CallbackContext) -> None:
        """Show help message about loyalty commands."""
        help_text = """
💎 *Бонусная программа*

Доступные команды:
/balance - Показать баланс баллов и уровень
/earn <баллы> [причина] - Начислить баллы (админ)
/spend <баллы> [причина] - Списать баллы
/history - История операций
/help_loyalty - Справка по бонусной программе

Баллы можно обменивать на скидки и специальные предложения. Чем больше баллов, тем выше уровень и выгоднее условия!
        """
        await update.message.reply_text(
            help_text,
            parse_mode='Markdown'
        )
    
    # Callback handlers for inline buttons
    async def handle_earn_callback(self, update: Update, context: CallbackContext) -> None:
        """Handle earn points callback."""
        query = update.callback_query
        await query.answer()
        
        # Extract data from callback
        data = query.data.split(':')
        if len(data) < 3:
            await query.message.reply_text("❌ Ошибка: неверный формат команды")
            return
            
        points = int(data[1])
        user_id = int(data[2])
        
        db = next(get_db())
        try:
            # Verify admin rights
            admin = db.query(User).filter(
                User.telegram_id == query.from_user.id,
                User.is_superuser == True
            ).first()
            
            if not admin:
                await query.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
                return
            
            # Add points
            service = LoyaltyService(db)
            transaction = service.earn_points({
                'user_id': user_id,
                'points': points,
                'description': f'Начисление администратором {admin.username}',
                'reference_id': f'tg_cb_{query.id}'
            })
            
            # Get user info
            user = db.query(User).get(user_id)
            
            # Notify admin
            await query.message.reply_text(
                f"✅ Пользователю {user.username or user.full_name} "
                f"начислено {points} баллов.\n"
                f"Новый баланс: {transaction.loyalty_account.points_balance} баллов"
            )
            
            # Notify user if possible
            if user.telegram_id:
                try:
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=f"🎉 Вам начислено {points} бонусных баллов!\n"
                              f"💳 Текущий баланс: {transaction.loyalty_account.points_balance} баллов"
                    )
                except Exception as e:
                    print(f"Failed to notify user: {e}")
            
        except Exception as e:
            await query.message.reply_text(
                "❌ Произошла ошибка при начислении баллов."
            )
            print(f"Error in handle_earn_callback: {e}")
        finally:
            db.close()
    
    async def handle_spend_callback(self, update: Update, context: CallbackContext) -> None:
        """Handle spend points callback."""
        query = update.callback_query
        await query.answer()
        
        # Implementation similar to handle_earn_callback
        # ...
        
    async def handle_history_callback(self, update: Update, context: CallbackContext) -> None:
        """Handle show history callback."""
        query = update.callback_query
        await query.answer()
        
        # Implementation similar to show_history
        # ...

def register_handlers(application):
    """Register all loyalty command handlers."""
    loyalty_handlers = LoyaltyCommandHandlers()
    
    # Register command handlers
    for command, handler in loyalty_handlers.commands:
        application.add_handler(CommandHandler(command, handler))
    
    # Register callback handlers
    for callback_prefix, handler in loyalty_handlers.callbacks.items():
        application.add_handler(CallbackQueryHandler(
            handler, pattern=f'^{callback_prefix}:'
        ))
    
    return loyalty_handlers
