"""
Test Configuration - Theory of Mind:
- Isolated test database = no production data corruption
- Reusable fixtures = DRY testing
- Mock external services = fast, reliable tests
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app
from app.database import Base, get_db
from app import models, auth
from app.config import get_settings

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create test client with database override"""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    """Create test user"""
    user = models.User(
        email="test@example.com",
        full_name="Test User",
        hashed_password=auth.get_password_hash("testpassword123"),
        tier="free",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_premium(db):
    """Create premium test user"""
    user = models.User(
        email="premium@example.com",
        full_name="Premium User",
        hashed_password=auth.get_password_hash("testpassword123"),
        tier="investor_pro",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Generate auth headers for test user"""
    access_token = auth.create_access_token(
        data={"sub": test_user.email},
        expires_delta=timedelta(minutes=30)
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def auth_headers_premium(test_user_premium):
    """Generate auth headers for premium user"""
    access_token = auth.create_access_token(
        data={"sub": test_user_premium.email},
        expires_delta=timedelta(minutes=30)
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def test_listings(db):
    """Create test listings"""
    listings = [
        models.Listing(
            address=f"{100 + i} Test St",
            city="Nashville",
            zip_code="37206",
            neighborhood="East Nashville",
            price=1800 + (i * 100),
            bedrooms=2,
            bathrooms=1.5,
            sqft=900 + (i * 50),
            property_type="apartment",
            description="Test listing",
            detail_url=f"https://zillow.com/test{i}",
            ingestion_date="20251101",
            deal_score=80 - i,
            days_on_market=5 + i,
        )
        for i in range(15)
    ]
    db.add_all(listings)
    db.commit()
    return listings


@pytest.fixture
def test_subscription(db, test_user_premium):
    """Create test subscription"""
    subscription = models.Subscription(
        user_id=test_user_premium.id,
        stripe_customer_id="cus_test123",
        stripe_subscription_id="sub_test123",
        tier="investor_pro",
        status="active",
        current_period_start=datetime.now(),
        current_period_end=datetime.now() + timedelta(days=30),
        cancel_at_period_end=False
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@pytest.fixture
def mock_stripe(mocker):
    """Mock Stripe API calls"""
    # Mock Customer.create
    mock_customer = mocker.MagicMock()
    mock_customer.id = "cus_test123"
    mocker.patch("stripe.Customer.create", return_value=mock_customer)

    # Mock Subscription.create
    mock_subscription = mocker.MagicMock()
    mock_subscription.id = "sub_test123"
    mock_subscription.status = "trialing"
    mock_subscription.current_period_start = int(datetime.now().timestamp())
    mock_subscription.current_period_end = int((datetime.now() + timedelta(days=30)).timestamp())
    mock_subscription.trial_end = int((datetime.now() + timedelta(days=7)).timestamp())
    mocker.patch("stripe.Subscription.create", return_value=mock_subscription)

    # Mock Subscription.modify
    mocker.patch("stripe.Subscription.modify", return_value=mock_subscription)

    # Mock billing_portal.Session.create
    mock_portal = mocker.MagicMock()
    mock_portal.url = "https://billing.stripe.com/session/test"
    mocker.patch("stripe.billing_portal.Session.create", return_value=mock_portal)

    return {
        "customer": mock_customer,
        "subscription": mock_subscription,
        "portal": mock_portal
    }
