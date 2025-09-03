""
Pydantic models for loyalty program data validation and serialization.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from app.models.loyalty import LoyaltyTier, TransactionType

# Base schemas
class PointsBase(BaseModel):
    """Base schema for points operations."""
    user_id: int = Field(..., description="ID of the user")
    points: int = Field(..., description="Number of points to process")
    description: Optional[str] = Field(None, description="Description of the transaction")
    reference_id: Optional[str] = Field(
        None, 
        description="External reference ID for the transaction"
    )

    @validator('points')
    def points_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Points must be a positive number')
        return v

# Request schemas
class PointsEarn(PointsBase):
    """Schema for earning points."""
    pass

class PointsSpend(PointsBase):
    """Schema for spending points."""
    @validator('points')
    def points_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Points must be a positive number')
        return v

class PointsAdjust(BaseModel):
    """Schema for adjusting points (admin only)."""
    user_id: int = Field(..., description="ID of the user")
    points: int = Field(..., description="Number of points to add (positive) or remove (negative)")
    description: str = Field(..., description="Reason for the adjustment")
    reference_id: Optional[str] = Field(
        None, 
        description="External reference ID for the transaction"
    )

# Response schemas
class TransactionResponse(BaseModel):
    """Schema for transaction response."""
    id: int
    user_id: int
    loyalty_account_id: int
    amount: int
    transaction_type: TransactionType
    description: Optional[str]
    reference_id: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class LoyaltyAccountResponse(BaseModel):
    """Schema for loyalty account response."""
    id: int
    user_id: int
    points_balance: int
    tier: LoyaltyTier
    total_points_earned: int
    total_points_spent: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TierBenefits(BaseModel):
    """Schema for tier benefits."""
    name: str
    discount: int
    priority_support: bool
    free_shipping_threshold: Optional[int]
    description: str

class AccountSummaryResponse(BaseModel):
    """Schema for account summary response."""
    user_id: int
    points_balance: int
    current_tier: str
    next_tier: Optional[str]
    points_to_next_tier: int
    total_points_earned: int
    total_points_spent: int
    tier_benefits: Dict[str, Any]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Webhook schemas
class WebhookEvent(BaseModel):
    """Base schema for webhook events."""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PointsEarnedEvent(WebhookEvent):
    """Schema for points earned event."""
    event_type: str = "points.earned"
    data: PointsEarn

class PointsSpentEvent(WebhookEvent):
    """Schema for points spent event."""
    event_type: str = "points.spent"
    data: PointsSpend

class TierUpgradedEvent(WebhookEvent):
    """Schema for tier upgraded event."""
    event_type: str = "tier.upgraded"
    data: Dict[str, Any] = Field(
        ...,
        example={
            "user_id": 12345,
            "old_tier": "silver",
            "new_tier": "gold"
        }
    )
