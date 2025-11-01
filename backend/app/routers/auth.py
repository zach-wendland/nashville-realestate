"""
Auth Routes - Theory of Mind:
- Registration = low friction (just email/password)
- Login = fast token generation
- /me endpoint = user sees their tier immediately
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import get_settings
from .. import models, schemas, auth

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/register", response_model=schemas.Token)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Register new user
    Theory of Mind: Immediate value = auto-login after signup
    """
    # Check if user exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        tier="free"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )

    # Get user response with tier info
    user_response = schemas.UserResponse(
        id=db_user.id,
        email=db_user.email,
        full_name=db_user.full_name,
        tier=db_user.tier,
        is_active=db_user.is_active,
        created_at=db_user.created_at,
        subscription_status=None,
        daily_views_remaining=settings.FREE_TIER_LIMIT
    )

    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.post("/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    Login user
    Theory of Mind: Fast auth = positive experience
    """
    user = auth.authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    # Get subscription status
    subscription_status = None
    if user.subscription:
        subscription_status = user.subscription.status

    # Calculate remaining views
    from datetime import date
    today = date.today().strftime("%Y%m%d")
    rate_limit_info = auth.check_rate_limit(db, user, today)

    user_response = schemas.UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        tier=user.tier,
        is_active=user.is_active,
        created_at=user.created_at,
        subscription_status=subscription_status,
        daily_views_remaining=rate_limit_info["remaining"]
    )

    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.get("/me", response_model=schemas.UserResponse)
async def get_me(current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    """
    Get current user info
    Theory of Mind: Users want to see their status at a glance
    """
    subscription_status = None
    if current_user.subscription:
        subscription_status = current_user.subscription.status

    # Calculate remaining views
    from datetime import date
    today = date.today().strftime("%Y%m%d")
    rate_limit_info = auth.check_rate_limit(db, current_user, today)

    return schemas.UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        tier=current_user.tier,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        subscription_status=subscription_status,
        daily_views_remaining=rate_limit_info["remaining"]
    )
