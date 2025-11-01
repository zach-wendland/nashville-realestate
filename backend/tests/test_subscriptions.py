"""
Subscriptions Tests - Theory of Mind:
- Test seamless upgrade flow = low friction conversion
- Test trial period = try before commitment
- Test easy cancellation = reduces hesitation
"""

import pytest
from fastapi import status
from datetime import datetime, timedelta


class TestCreateSubscription:
    """Test subscription creation"""

    def test_create_subscription_success(self, client, auth_headers, test_user, db, mock_stripe):
        """Should create new subscription"""
        response = client.post(
            "/subscriptions/create",
            headers=auth_headers,
            json={
                "tier": "renter_plus",
                "payment_method_id": "pm_test123"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tier"] == "renter_plus"
        assert data["status"] == "trialing"
        assert "trial_end" in data

        # User tier should be updated
        db.refresh(test_user)
        assert test_user.tier == "renter_plus"

    def test_create_subscription_invalid_tier(self, client, auth_headers, mock_stripe):
        """Should reject invalid tier"""
        response = client.post(
            "/subscriptions/create",
            headers=auth_headers,
            json={
                "tier": "invalid_tier",
                "payment_method_id": "pm_test123"
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_subscription_already_subscribed(self, client, auth_headers_premium, test_subscription, mock_stripe):
        """Should reject if user already has active subscription"""
        response = client.post(
            "/subscriptions/create",
            headers=auth_headers_premium,
            json={
                "tier": "investor_pro",
                "payment_method_id": "pm_test123"
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already" in response.json()["detail"].lower()

    def test_create_subscription_with_trial(self, client, auth_headers, mock_stripe):
        """
        Theory of Mind: Trial period = risk-free value demonstration
        Users can experience premium before paying
        """
        response = client.post(
            "/subscriptions/create",
            headers=auth_headers,
            json={
                "tier": "investor_pro",
                "payment_method_id": "pm_test123"
            }
        )

        data = response.json()
        assert data["status"] == "trialing"
        assert data["trial_end"] is not None


class TestCancelSubscription:
    """Test subscription cancellation"""

    def test_cancel_subscription_success(self, client, auth_headers_premium, test_subscription, mock_stripe):
        """Should cancel subscription at period end"""
        response = client.post(
            "/subscriptions/cancel",
            headers=auth_headers_premium
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "period_end" in data
        assert "cancel" in data["message"].lower()

    def test_cancel_subscription_not_found(self, client, auth_headers, mock_stripe):
        """Should return 404 if no subscription"""
        response = client.post(
            "/subscriptions/cancel",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cancel_at_period_end_not_immediate(self, client, auth_headers_premium, test_subscription, db, mock_stripe):
        """
        Theory of Mind: Cancel at period end = user gets full value
        Doesn't feel cheated, more likely to re-subscribe later
        """
        response = client.post(
            "/subscriptions/cancel",
            headers=auth_headers_premium
        )

        # Subscription should still be active until period end
        db.refresh(test_subscription)
        assert test_subscription.status == "active"
        assert test_subscription.cancel_at_period_end is True


class TestReactivateSubscription:
    """Test subscription reactivation"""

    def test_reactivate_subscription(self, client, auth_headers_premium, test_subscription, db, mock_stripe):
        """Should reactivate canceled subscription"""
        # First cancel
        test_subscription.cancel_at_period_end = True
        db.commit()

        # Then reactivate
        response = client.post(
            "/subscriptions/reactivate",
            headers=auth_headers_premium
        )

        assert response.status_code == status.HTTP_200_OK
        assert "reactivate" in response.json()["message"].lower()

        db.refresh(test_subscription)
        assert test_subscription.cancel_at_period_end is False

    def test_reactivate_not_canceled(self, client, auth_headers_premium, test_subscription, mock_stripe):
        """Should reject reactivation if not canceled"""
        response = client.post(
            "/subscriptions/reactivate",
            headers=auth_headers_premium
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reactivate_easy_win_back(self, client, auth_headers_premium, test_subscription, db, mock_stripe):
        """
        Theory of Mind: Easy reactivation = win back regretful cancellations
        Captures FOMO when they realize what they're losing
        """
        # Cancel
        test_subscription.cancel_at_period_end = True
        db.commit()

        # Reactivate with single click
        response = client.post(
            "/subscriptions/reactivate",
            headers=auth_headers_premium
        )

        # Should be instant
        assert response.status_code == status.HTTP_200_OK
        db.refresh(test_subscription)
        assert test_subscription.cancel_at_period_end is False


class TestCustomerPortal:
    """Test Stripe customer portal"""

    def test_get_portal_url(self, client, auth_headers_premium, test_subscription, mock_stripe):
        """Should return portal URL"""
        response = client.get(
            "/subscriptions/portal-url",
            headers=auth_headers_premium
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "url" in data
        assert data["url"].startswith("https://")

    def test_get_portal_url_no_subscription(self, client, auth_headers):
        """Should return 404 if no subscription"""
        response = client.get(
            "/subscriptions/portal-url",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_portal_self_service(self, client, auth_headers_premium, test_subscription, mock_stripe):
        """
        Theory of Mind: Self-service portal = reduces support burden
        Users feel in control of their billing
        """
        response = client.get(
            "/subscriptions/portal-url",
            headers=auth_headers_premium
        )

        # Should get portal URL for self-service
        assert response.status_code == status.HTTP_200_OK
        assert "billing" in response.json()["url"]


class TestGetSubscription:
    """Test subscription retrieval"""

    def test_get_subscription(self, client, auth_headers_premium, test_subscription):
        """Should return current subscription"""
        response = client.get(
            "/subscriptions",
            headers=auth_headers_premium
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tier"] == "investor_pro"
        assert data["status"] == "active"

    def test_get_subscription_not_found(self, client, auth_headers):
        """Should return 404 if no subscription"""
        response = client.get(
            "/subscriptions",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestStripeWebhooks:
    """Test Stripe webhook handling"""

    def test_webhook_subscription_updated(self, client, test_subscription, db):
        """Should handle subscription.updated webhook"""
        # Simulate Stripe webhook
        webhook_data = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": test_subscription.stripe_subscription_id,
                    "status": "active",
                    "current_period_start": int(datetime.now().timestamp()),
                    "current_period_end": int((datetime.now() + timedelta(days=30)).timestamp()),
                    "cancel_at_period_end": False
                }
            }
        }

        # Mock webhook verification
        import stripe
        from unittest.mock import patch

        with patch('stripe.Webhook.construct_event', return_value=webhook_data):
            response = client.post(
                "/subscriptions/webhook",
                json=webhook_data,
                headers={"stripe-signature": "test_signature"}
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["received"] is True

    def test_webhook_subscription_deleted(self, client, test_subscription, test_user_premium, db):
        """Should handle subscription.deleted webhook and downgrade user"""
        webhook_data = {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": test_subscription.stripe_subscription_id
                }
            }
        }

        import stripe
        from unittest.mock import patch

        with patch('stripe.Webhook.construct_event', return_value=webhook_data):
            response = client.post(
                "/subscriptions/webhook",
                json=webhook_data,
                headers={"stripe-signature": "test_signature"}
            )

        assert response.status_code == status.HTTP_200_OK

        # User should be downgraded
        db.refresh(test_user_premium)
        assert test_user_premium.tier == "free"

    def test_webhook_payment_failed(self, client, test_subscription, db):
        """Should handle payment failure"""
        webhook_data = {
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "subscription": test_subscription.stripe_subscription_id
                }
            }
        }

        import stripe
        from unittest.mock import patch

        with patch('stripe.Webhook.construct_event', return_value=webhook_data):
            response = client.post(
                "/subscriptions/webhook",
                json=webhook_data,
                headers={"stripe-signature": "test_signature"}
            )

        assert response.status_code == status.HTTP_200_OK

        # Subscription should be marked past_due
        db.refresh(test_subscription)
        assert test_subscription.status == "past_due"


class TestTheoryOfMind:
    """Test psychological conversion principles"""

    def test_trial_reduces_commitment_anxiety(self, client, auth_headers, mock_stripe):
        """
        Theory of Mind: 7-day trial = experience value before paying
        Reduces fear of wasting money
        """
        response = client.post(
            "/subscriptions/create",
            headers=auth_headers,
            json={
                "tier": "renter_plus",
                "payment_method_id": "pm_test123"
            }
        )

        data = response.json()
        assert data["status"] == "trialing"
        # Trial gives them time to see value

    def test_easy_cancellation_reduces_signup_friction(self, client, auth_headers_premium, test_subscription, mock_stripe):
        """
        Theory of Mind: Easy cancellation = less fear of commitment
        "I can always cancel" makes signup easier
        """
        response = client.post(
            "/subscriptions/cancel",
            headers=auth_headers_premium
        )

        # Should be simple, one-click cancellation
        assert response.status_code == status.HTTP_200_OK
        # No hoops to jump through

    def test_immediate_tier_upgrade_gratification(self, client, auth_headers, test_user, db, mock_stripe):
        """
        Theory of Mind: Instant tier upgrade = immediate gratification
        Users see benefits right away
        """
        response = client.post(
            "/subscriptions/create",
            headers=auth_headers,
            json={
                "tier": "investor_pro",
                "payment_method_id": "pm_test123"
            }
        )

        # Tier should be upgraded immediately
        db.refresh(test_user)
        assert test_user.tier == "investor_pro"
        # No waiting period for benefits

    def test_transparent_billing_builds_trust(self, client, auth_headers_premium, test_subscription):
        """
        Theory of Mind: Access to billing portal = transparency
        Users trust when they control their billing
        """
        response = client.get(
            "/subscriptions/portal-url",
            headers=auth_headers_premium
        )

        # Should provide self-service access
        assert response.status_code == status.HTTP_200_OK
        # No hiding billing information
