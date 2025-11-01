"""
Database Models - Theory of Mind:
- User tiers = gate features, create upgrade desire
- Activity tracking = enforce rate limits fairly
- Subscription status = clear payment state
- Indexes on common queries = fast user experience
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    """
    User model - Theory of Mind:
    - Email as primary ID = familiar login method
    - Tier column = determines feature access
    - created_at = show account age (trust building)
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    tier = Column(String, default="free")  # free, renter_plus, investor_pro, enterprise
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    activity = relationship("UserActivity", back_populates="user")
    saved_searches = relationship("SavedSearch", back_populates="user")


class Subscription(Base):
    """
    Subscription model - Theory of Mind:
    - Stripe IDs = payment provider integration
    - Status column = handle trial, active, canceled states
    - trial_end = show trial deadline (urgency)
    """
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    stripe_customer_id = Column(String, index=True)
    stripe_subscription_id = Column(String, index=True)
    tier = Column(String, nullable=False)  # renter_plus, investor_pro, enterprise
    status = Column(String, default="trialing")  # trialing, active, canceled, past_due
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    trial_end = Column(DateTime(timezone=True))
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="subscription")


class Listing(Base):
    """
    Listing model - Theory of Mind:
    - Rich data fields = comprehensive property info
    - deal_score = gamification, urgency
    - days_on_market = scarcity indicator
    - Indexes on filters = fast search results
    """
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, nullable=False)
    city = Column(String, index=True)
    zip_code = Column(String, index=True)
    neighborhood = Column(String, index=True)
    price = Column(Integer, index=True)
    bedrooms = Column(Integer, index=True)
    bathrooms = Column(Float)
    sqft = Column(Integer)
    property_type = Column(String, index=True)
    description = Column(Text)
    image_url = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    days_on_market = Column(Integer)
    deal_score = Column(Integer)  # 0-100, higher = better deal
    amenities = Column(Text)  # JSON string of amenities
    detail_url = Column(String, unique=True)  # Zillow URL
    ingestion_date = Column(String, index=True)  # YYYYMMDD format
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Composite index for common query patterns
    __table_args__ = (
        Index('idx_price_beds', 'price', 'bedrooms'),
        Index('idx_zip_price', 'zip_code', 'price'),
    )


class UserActivity(Base):
    """
    User Activity model - Theory of Mind:
    - Track listing views = enforce rate limits
    - Daily reset = users understand "per day" limit
    - view_date index = fast rate limit checks
    """
    __tablename__ = "user_activity"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    action = Column(String)  # view, save, contact
    view_date = Column(String, index=True)  # YYYYMMDD for daily limits
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="activity")

    # Index for rate limiting queries
    __table_args__ = (
        Index('idx_user_date', 'user_id', 'view_date'),
    )


class SavedSearch(Base):
    """
    Saved Search model - Theory of Mind:
    - Save filters = convenience, repeat usage
    - Alert frequency = user control
    - Premium feature indicator
    """
    __tablename__ = "saved_searches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    filters = Column(Text)  # JSON string of filter criteria
    alert_frequency = Column(String, default="daily")  # daily, weekly, never
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="saved_searches")
