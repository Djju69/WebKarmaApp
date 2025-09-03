""
Loyalty program API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.base import get_db
from app.schemas.loyalty import (
    PointsEarn, PointsSpend, PointsAdjust,
    TransactionResponse, LoyaltyAccountResponse, AccountSummaryResponse
)
from app.services.loyalty.service import LoyaltyService
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.post("/earn", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
asdef earn_points(
    points_data: PointsEarn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Earn loyalty points for a user.
    """
    # Check if current user is admin or the same user
    if not current_user.is_superuser and current_user.id != points_data.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    service = LoyaltyService(db)
    try:
        transaction = service.earn_points(points_data)
        return transaction
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/spend", response_model=TransactionResponse)
asdef spend_points(
    points_data: PointsSpend,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Spend loyalty points from a user's account.
    """
    # Check if current user is admin or the same user
    if not current_user.is_superuser and current_user.id != points_data.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    service = LoyaltyService(db)
    transaction = service.spend_points(points_data)
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough points"
        )
    
    return transaction

@router.post("/adjust", response_model=TransactionResponse)
asdef adjust_points(
    points_data: PointsAdjust,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Adjust points (admin only).
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    service = LoyaltyService(db)
    try:
        transaction = service.adjust_points(points_data)
        return transaction
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/account/{user_id}", response_model=AccountSummaryResponse)
asdef get_account_summary(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get loyalty account summary for a user.
    """
    # Check if current user is admin or the same user
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    service = LoyaltyService(db)
    return service.get_account_summary(user_id)

@router.get("/transactions/{user_id}", response_model=List[TransactionResponse])
asdef get_transactions(
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get transaction history for a user.
    """
    # Check if current user is admin or the same user
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    from app.models.loyalty import Transaction
    
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return transactions
