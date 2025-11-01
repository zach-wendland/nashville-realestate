"""
Auth Tests - Theory of Mind:
- Test registration flow = ensure smooth onboarding
- Test login = verify fast authentication
- Test rate limit visibility = users see their status
"""

import pytest
from fastapi import status


class TestRegistration:
    """Test user registration"""

    def test_register_new_user(self, client, db):
        """Should register new user and return token"""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "full_name": "New User"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["tier"] == "free"
        assert data["user"]["daily_views_remaining"] == 10  # Free tier limit

    def test_register_duplicate_email(self, client, test_user):
        """Should reject duplicate email"""
        response = client.post(
            "/auth/register",
            json={
                "email": test_user.email,
                "password": "password123",
                "full_name": "Duplicate User"
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        """Should reject invalid email format"""
        response = client.post(
            "/auth/register",
            json={
                "email": "notanemail",
                "password": "password123",
                "full_name": "Invalid Email"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_short_password(self, client):
        """Should reject password shorter than 8 characters"""
        response = client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "short",
                "full_name": "Short Pass"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLogin:
    """Test user login"""

    def test_login_success(self, client, test_user):
        """Should login existing user and return token"""
        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == test_user.email
        assert "daily_views_remaining" in data["user"]

    def test_login_wrong_password(self, client, test_user):
        """Should reject incorrect password"""
        response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Should reject non-existent user"""
        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_shows_subscription_status(self, client, test_user_premium, test_subscription):
        """Should show subscription status for premium users"""
        response = client.post(
            "/auth/login",
            json={
                "email": test_user_premium.email,
                "password": "testpassword123"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user"]["subscription_status"] == "active"
        assert data["user"]["tier"] == "investor_pro"


class TestCurrentUser:
    """Test /me endpoint"""

    def test_get_current_user(self, client, auth_headers, test_user):
        """Should return current user info"""
        response = client.get("/auth/me", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user.email
        assert data["tier"] == "free"
        assert "daily_views_remaining" in data

    def test_get_current_user_unauthorized(self, client):
        """Should reject request without auth token"""
        response = client.get("/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_invalid_token(self, client):
        """Should reject invalid token"""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalidtoken"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_shows_rate_limit(self, client, auth_headers, test_user, db):
        """Should show remaining views for current day"""
        from datetime import date
        from app import models

        # Create some views for today
        today = date.today().strftime("%Y%m%d")
        for i in range(3):
            view = models.UserActivity(
                user_id=test_user.id,
                listing_id=1,
                view_date=today,
                action="view"
            )
            db.add(view)
        db.commit()

        response = client.get("/auth/me", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["daily_views_remaining"] == 7  # 10 - 3


class TestTheoryOfMind:
    """Test psychological aspects of auth flow"""

    def test_immediate_login_after_registration(self, client):
        """
        Theory of Mind: Auto-login after registration = immediate value
        User doesn't have to login separately
        """
        response = client.post(
            "/auth/register",
            json={
                "email": "instant@example.com",
                "password": "password123",
                "full_name": "Instant User"
            }
        )

        # Should receive token immediately
        assert "access_token" in response.json()
        # Should be able to use that token right away
        token = response.json()["access_token"]
        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == status.HTTP_200_OK

    def test_rate_limit_visibility(self, client, auth_headers):
        """
        Theory of Mind: Show remaining views = transparency builds trust
        Also creates urgency when limit is low
        """
        response = client.get("/auth/me", headers=auth_headers)

        data = response.json()
        assert "daily_views_remaining" in data
        assert isinstance(data["daily_views_remaining"], int)
        assert data["daily_views_remaining"] >= 0

    def test_free_tier_default(self, client):
        """
        Theory of Mind: Everyone starts free = low barrier to entry
        Upgrade happens after they see value
        """
        response = client.post(
            "/auth/register",
            json={
                "email": "freetier@example.com",
                "password": "password123",
                "full_name": "Free User"
            }
        )

        assert response.json()["user"]["tier"] == "free"
        assert response.json()["user"]["daily_views_remaining"] == 10
