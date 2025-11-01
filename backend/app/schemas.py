"""
Pydantic Schemas - Theory of Mind:
- Clear validation = immediate error feedback
- Optional fields = flexible API usage
- Computed fields = show upgrade benefits
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    tier: str
    is_active: bool
    created_at: datetime
    subscription_status: Optional[str] = None
    daily_views_remaining: Optional[int] = None  # Theory of Mind: Show scarcity

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# Listing Schemas
class ListingBase(BaseModel):
    address: str
    city: str
    zip_code: str
    neighborhood: str
    price: int
    bedrooms: int
    bathrooms: float
    sqft: Optional[int] = None
    property_type: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    days_on_market: Optional[int] = None
    deal_score: Optional[int] = None
    amenities: Optional[str] = None


class ListingCreate(ListingBase):
    detail_url: str
    ingestion_date: str


class ListingResponse(ListingBase):
    id: int
    detail_url: str
    created_at: datetime
    is_locked: bool = False  # Theory of Mind: Show premium-only listings

    class Config:
        from_attributes = True


class ListingListResponse(BaseModel):
    """
    Theory of Mind: Show what they're missing
    - total = full count (shows locked listings exist)
    - accessible = what they can see
    - upgrade_message = clear CTA
    """
    listings: List[ListingResponse]
    total: int
    accessible: int
    page: int
    page_size: int
    has_more: bool
    upgrade_message: Optional[str] = None


# Filter Schemas
class ListingFilters(BaseModel):
    zip_code: Optional[str] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    bedrooms: Optional[int] = None
    property_type: Optional[str] = None
    neighborhood: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# Subscription Schemas
class SubscriptionCreate(BaseModel):
    tier: str = Field(..., regex="^(renter_plus|investor_pro|enterprise)$")
    payment_method_id: str  # Stripe payment method ID


class SubscriptionResponse(BaseModel):
    id: int
    tier: str
    status: str
    current_period_end: Optional[datetime]
    trial_end: Optional[datetime]
    cancel_at_period_end: bool

    class Config:
        from_attributes = True


# Stats Schemas
class MarketStats(BaseModel):
    """
    Theory of Mind: Show market intelligence
    - Real stats = credibility
    - Top deals = shows what they're missing
    """
    total_listings: int
    avg_price: float
    min_price: int
    max_price: int
    avg_deal_score: float
    top_deals: List[ListingResponse] = []
    upgrade_message: Optional[str] = None


class PriceHistoryPoint(BaseModel):
    month: str
    avg_price: int


class PriceHistory(BaseModel):
    data: List[PriceHistoryPoint]
    period: str  # "6-month", "30-day", etc.


# Saved Search Schemas
class SavedSearchCreate(BaseModel):
    name: str
    filters: dict  # JSON object with filter criteria
    alert_frequency: str = "never"  # daily, weekly, never


class SavedSearchResponse(BaseModel):
    id: int
    name: str
    filters: dict
    alert_frequency: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Error Schemas
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    upgrade_required: bool = False  # Theory of Mind: Clear upgrade signal


# Webhook Schemas
class StripeWebhookEvent(BaseModel):
    type: str
    data: dict
