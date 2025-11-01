"""Initial schema for Nashville Rentals SaaS

Revision ID: 001
Revises:
Create Date: 2025-11-01 00:00:00

Theory of Mind:
- Users table = authentication and tier management
- Subscriptions table = Stripe integration
- Listings table = property data
- UserActivity table = rate limit enforcement
- SavedSearches table = premium feature
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('tier', sa.String(), nullable=True, server_default='free'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('stripe_customer_id', sa.String(), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(), nullable=True),
        sa.Column('tier', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True, server_default='trialing'),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscriptions_id'), 'subscriptions', ['id'], unique=False)
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=True)
    op.create_index(op.f('ix_subscriptions_stripe_customer_id'), 'subscriptions', ['stripe_customer_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_stripe_subscription_id'), 'subscriptions', ['stripe_subscription_id'], unique=False)

    # Create listings table
    op.create_table(
        'listings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('address', sa.String(), nullable=False),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('zip_code', sa.String(), nullable=True),
        sa.Column('neighborhood', sa.String(), nullable=True),
        sa.Column('price', sa.Integer(), nullable=True),
        sa.Column('bedrooms', sa.Integer(), nullable=True),
        sa.Column('bathrooms', sa.Float(), nullable=True),
        sa.Column('sqft', sa.Integer(), nullable=True),
        sa.Column('property_type', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('days_on_market', sa.Integer(), nullable=True),
        sa.Column('deal_score', sa.Integer(), nullable=True),
        sa.Column('amenities', sa.Text(), nullable=True),
        sa.Column('detail_url', sa.String(), nullable=True),
        sa.Column('ingestion_date', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_listings_id'), 'listings', ['id'], unique=False)
    op.create_index(op.f('ix_listings_city'), 'listings', ['city'], unique=False)
    op.create_index(op.f('ix_listings_zip_code'), 'listings', ['zip_code'], unique=False)
    op.create_index(op.f('ix_listings_neighborhood'), 'listings', ['neighborhood'], unique=False)
    op.create_index(op.f('ix_listings_price'), 'listings', ['price'], unique=False)
    op.create_index(op.f('ix_listings_bedrooms'), 'listings', ['bedrooms'], unique=False)
    op.create_index(op.f('ix_listings_property_type'), 'listings', ['property_type'], unique=False)
    op.create_index(op.f('ix_listings_ingestion_date'), 'listings', ['ingestion_date'], unique=False)
    op.create_index(op.f('ix_listings_detail_url'), 'listings', ['detail_url'], unique=True)

    # Composite indexes for common query patterns
    op.create_index('idx_price_beds', 'listings', ['price', 'bedrooms'], unique=False)
    op.create_index('idx_zip_price', 'listings', ['zip_code', 'price'], unique=False)

    # Create user_activity table
    op.create_table(
        'user_activity',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('listing_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(), nullable=True),
        sa.Column('view_date', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['listing_id'], ['listings.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_activity_id'), 'user_activity', ['id'], unique=False)
    op.create_index(op.f('ix_user_activity_view_date'), 'user_activity', ['view_date'], unique=False)

    # Composite index for rate limiting queries
    op.create_index('idx_user_date', 'user_activity', ['user_id', 'view_date'], unique=False)

    # Create saved_searches table
    op.create_table(
        'saved_searches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('filters', sa.Text(), nullable=True),
        sa.Column('alert_frequency', sa.String(), nullable=True, server_default='daily'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_saved_searches_id'), 'saved_searches', ['id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('saved_searches')
    op.drop_table('user_activity')
    op.drop_table('listings')
    op.drop_table('subscriptions')
    op.drop_table('users')
