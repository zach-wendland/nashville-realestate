"""
Authentication - Theory of Mind:
- JWT tokens = stateless, scalable
- Password hashing = security (users trust us with data)
- Token expiry = balance security vs convenience
- Clear error messages = reduce user frustration
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from . import models, schemas

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password for storage"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    Theory of Mind: Expiry forces re-auth = security without annoying users
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    """
    Authenticate user by email/password
    Theory of Mind: Clear failure = user knows what to fix
    """
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Get current user from JWT token
    Theory of Mind: Dependency injection = automatic auth on protected routes
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Ensure user is active
    Theory of Mind: Account suspension = clear reason, appeal process
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_user_tier_limit(tier: str) -> int:
    """
    Get daily listing view limit for user tier
    Theory of Mind: Clear limits = users understand tiers
    """
    tier_limits = {
        "free": settings.FREE_TIER_LIMIT,
        "renter_plus": settings.RENTER_PLUS_LIMIT,
        "investor_pro": settings.INVESTOR_PRO_LIMIT,
        "enterprise": settings.ENTERPRISE_LIMIT,
    }
    return tier_limits.get(tier, settings.FREE_TIER_LIMIT)


def check_rate_limit(db: Session, user: models.User, today: str) -> dict:
    """
    Check if user has exceeded daily rate limit
    Theory of Mind:
    - Show remaining views = transparency, urgency
    - Clear upgrade message = conversion opportunity
    """
    limit = get_user_tier_limit(user.tier)

    # Count today's views
    views_today = (
        db.query(models.UserActivity)
        .filter(
            models.UserActivity.user_id == user.id,
            models.UserActivity.view_date == today,
            models.UserActivity.action == "view"
        )
        .count()
    )

    remaining = max(0, limit - views_today)
    exceeded = views_today >= limit

    return {
        "exceeded": exceeded,
        "limit": limit,
        "used": views_today,
        "remaining": remaining,
        "upgrade_message": "Upgrade to see unlimited listings" if exceeded and user.tier == "free" else None
    }
