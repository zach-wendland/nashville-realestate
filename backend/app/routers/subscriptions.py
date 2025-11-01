"""
Subscriptions Routes - Theory of Mind:
- Seamless upgrade = low friction conversion
- Trial period = try before commitment
- Clear pricing = builds trust
- Easy cancellation = reduces hesitation
"""

import stripe
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import get_settings
from .. import models, schemas, auth

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])
settings = get_settings()
stripe.api_key = settings.STRIPE_SECRET_KEY


# Tier to Stripe Price ID mapping
TIER_TO_PRICE = {
    "renter_plus": settings.STRIPE_PRICE_RENTER_PLUS,
    "investor_pro": settings.STRIPE_PRICE_INVESTOR_PRO,
    "enterprise": settings.STRIPE_PRICE_ENTERPRISE,
}


@router.post("/create", response_model=schemas.SubscriptionResponse)
async def create_subscription(
    subscription_data: schemas.SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Create new subscription
    Theory of Mind: Immediate activation = instant gratification
    """
    # Check if user already has subscription
    if current_user.subscription and current_user.subscription.status in ["active", "trialing"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active subscription"
        )

    # Validate tier
    if subscription_data.tier not in TIER_TO_PRICE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription tier"
        )

    try:
        # Create or retrieve Stripe customer
        if current_user.subscription and current_user.subscription.stripe_customer_id:
            customer_id = current_user.subscription.stripe_customer_id
        else:
            customer = stripe.Customer.create(
                email=current_user.email,
                payment_method=subscription_data.payment_method_id,
                invoice_settings={
                    "default_payment_method": subscription_data.payment_method_id,
                },
                metadata={
                    "user_id": current_user.id,
                }
            )
            customer_id = customer.id

        # Create Stripe subscription with 7-day trial
        # Theory of Mind: Trial = risk-free way to experience value
        stripe_subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": TIER_TO_PRICE[subscription_data.tier]}],
            trial_period_days=7,
            metadata={
                "user_id": current_user.id,
                "tier": subscription_data.tier,
            }
        )

        # Update or create subscription in database
        if current_user.subscription:
            db_subscription = current_user.subscription
            db_subscription.stripe_customer_id = customer_id
            db_subscription.stripe_subscription_id = stripe_subscription.id
            db_subscription.tier = subscription_data.tier
            db_subscription.status = stripe_subscription.status
            db_subscription.current_period_start = datetime.fromtimestamp(
                stripe_subscription.current_period_start
            )
            db_subscription.current_period_end = datetime.fromtimestamp(
                stripe_subscription.current_period_end
            )
            if stripe_subscription.trial_end:
                db_subscription.trial_end = datetime.fromtimestamp(
                    stripe_subscription.trial_end
                )
        else:
            db_subscription = models.Subscription(
                user_id=current_user.id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=stripe_subscription.id,
                tier=subscription_data.tier,
                status=stripe_subscription.status,
                current_period_start=datetime.fromtimestamp(
                    stripe_subscription.current_period_start
                ),
                current_period_end=datetime.fromtimestamp(
                    stripe_subscription.current_period_end
                ),
                trial_end=datetime.fromtimestamp(stripe_subscription.trial_end)
                if stripe_subscription.trial_end
                else None,
            )
            db.add(db_subscription)

        # Update user tier
        current_user.tier = subscription_data.tier

        db.commit()
        db.refresh(db_subscription)

        return schemas.SubscriptionResponse.model_validate(db_subscription)

    except stripe.error.CardError as e:
        # Card declined
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Card declined: {e.user_message}"
        )
    except stripe.error.StripeError as e:
        # Other Stripe errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment error: {str(e)}"
        )


@router.post("/cancel")
async def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Cancel subscription
    Theory of Mind: Easy cancellation = trust, less friction to sign up
    """
    if not current_user.subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )

    try:
        # Cancel at period end (let them use until billing cycle ends)
        stripe.Subscription.modify(
            current_user.subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )

        # Update database
        current_user.subscription.cancel_at_period_end = True
        db.commit()

        return {
            "message": "Subscription will cancel at period end",
            "period_end": current_user.subscription.current_period_end
        }

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error canceling subscription: {str(e)}"
        )


@router.post("/reactivate")
async def reactivate_subscription(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Reactivate canceled subscription
    Theory of Mind: Easy win-back = capture regret/FOMO
    """
    if not current_user.subscription or not current_user.subscription.cancel_at_period_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No canceled subscription to reactivate"
        )

    try:
        # Remove cancel_at_period_end flag
        stripe.Subscription.modify(
            current_user.subscription.stripe_subscription_id,
            cancel_at_period_end=False
        )

        # Update database
        current_user.subscription.cancel_at_period_end = False
        db.commit()

        return {"message": "Subscription reactivated successfully"}

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reactivating subscription: {str(e)}"
        )


@router.get("/portal-url")
async def get_portal_url(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Get Stripe customer portal URL
    Theory of Mind: Self-service billing = reduces support burden
    """
    if not current_user.subscription or not current_user.subscription.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )

    try:
        # Create portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.subscription.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/dashboard",
        )

        return {"url": portal_session.url}

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating portal session: {str(e)}"
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    """
    Handle Stripe webhook events
    Theory of Mind: Automated status updates = seamless experience
    """
    payload = await request.body()

    # Verify webhook signature
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle different event types
    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "customer.subscription.created":
        # Subscription created (already handled in create endpoint)
        pass

    elif event_type == "customer.subscription.updated":
        # Subscription status changed
        subscription_id = data["id"]
        db_subscription = db.query(models.Subscription).filter(
            models.Subscription.stripe_subscription_id == subscription_id
        ).first()

        if db_subscription:
            db_subscription.status = data["status"]
            db_subscription.current_period_start = datetime.fromtimestamp(
                data["current_period_start"]
            )
            db_subscription.current_period_end = datetime.fromtimestamp(
                data["current_period_end"]
            )
            db_subscription.cancel_at_period_end = data.get("cancel_at_period_end", False)

            # Update user tier based on subscription status
            if data["status"] in ["active", "trialing"]:
                db_subscription.user.tier = db_subscription.tier
            elif data["status"] in ["canceled", "past_due", "unpaid"]:
                db_subscription.user.tier = "free"

            db.commit()

    elif event_type == "customer.subscription.deleted":
        # Subscription canceled/ended
        subscription_id = data["id"]
        db_subscription = db.query(models.Subscription).filter(
            models.Subscription.stripe_subscription_id == subscription_id
        ).first()

        if db_subscription:
            db_subscription.status = "canceled"
            db_subscription.user.tier = "free"
            db.commit()

    elif event_type == "customer.subscription.trial_will_end":
        # Trial ending in 3 days - could send email reminder
        # Theory of Mind: Reminder = chance to prevent churn
        pass

    elif event_type == "invoice.payment_failed":
        # Payment failed - update subscription status
        subscription_id = data.get("subscription")
        if subscription_id:
            db_subscription = db.query(models.Subscription).filter(
                models.Subscription.stripe_subscription_id == subscription_id
            ).first()
            if db_subscription:
                db_subscription.status = "past_due"
                db.commit()

    elif event_type == "invoice.payment_succeeded":
        # Payment succeeded - ensure subscription is active
        subscription_id = data.get("subscription")
        if subscription_id:
            db_subscription = db.query(models.Subscription).filter(
                models.Subscription.stripe_subscription_id == subscription_id
            ).first()
            if db_subscription and db_subscription.status == "past_due":
                db_subscription.status = "active"
                db_subscription.user.tier = db_subscription.tier
                db.commit()

    return {"received": True}


@router.get("", response_model=schemas.SubscriptionResponse)
async def get_subscription(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """Get current user's subscription"""
    if not current_user.subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )

    return schemas.SubscriptionResponse.model_validate(current_user.subscription)
