""
Initialize the database with tables and initial data.
"""
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.base import Base, engine
from app.core.config import settings
from app.models.user import User
from app.models.loyalty import LoyaltyAccount
from sqlalchemy.orm import sessionmaker
from app.core.security import get_password_hash

def init_db() -> None:
    """Initialize the database with tables and initial data."""
    # Create all tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Create a new session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Create admin user if not exists
        admin = db.query(User).filter(User.email == settings.FIRST_SUPERUSER).first()
        if not admin:
            print("Creating admin user...")
            admin = User(
                email=settings.FIRST_SUPERUSER,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                is_superuser=True,
                is_active=True,
                full_name="Admin"
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"Admin user created with email: {admin.email}")
        
        # Create loyalty account for admin if not exists
        loyalty_account = db.query(LoyaltyAccount).filter(
            LoyaltyAccount.user_id == admin.id
        ).first()
        
        if not loyalty_account:
            print("Creating loyalty account for admin...")
            loyalty_account = LoyaltyAccount(
                user_id=admin.id,
                points_balance=1000,
                tier="platinum",
                total_points_earned=1000,
                total_points_spent=0
            )
            db.add(loyalty_account)
            db.commit()
            print("Loyalty account created for admin")
        
        print("Database initialized successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
