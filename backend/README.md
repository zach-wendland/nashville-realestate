# Nashville Rentals API - Backend

FastAPI backend for Nashville rental property SaaS with freemium monetization model.

## Theory of Mind Architecture

This backend is designed with psychological principles to maximize conversions:

### 🧠 Scarcity Psychology
- **Rate limiting** enforces daily view limits (10 for free, unlimited for paid)
- **Transparent limits** show users exactly how many views remain
- **FOMO creation** by showing total listings while restricting access

### 💎 Value Demonstration
- **Free tier provides real value** (10 listings/day = enough to see usefulness)
- **Premium features visible but locked** (market stats, top deals)
- **Trial period** (7 days) lets users experience full value risk-free

### 🎯 Conversion Triggers
- **Upgrade prompts at friction points** (when rate limit exceeded)
- **Clear CTAs** in API responses (upgrade_message field)
- **Immediate gratification** (tier upgrades happen instantly)

### 🤝 Trust Building
- **Easy cancellation** (cancel at period end, keep access)
- **Self-service billing portal** (full transparency)
- **Fair rate limiting** (daily reset, counts actual views)

## Tech Stack

- **FastAPI** - Modern, fast Python web framework
- **SQLAlchemy** - ORM for database operations
- **PostgreSQL** - Production database
- **Stripe** - Payment processing
- **JWT** - Authentication tokens
- **Redis** - Rate limiting (optional, in-memory fallback)
- **Pytest** - Testing framework

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Stripe account (for payments)
- Redis (optional, for rate limiting)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd nashville-realestate/backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

Required environment variables:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/nashville_rentals
SECRET_KEY=your-secret-key-min-32-characters
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
```

5. **Create database**
```bash
createdb nashville_rentals
```

6. **Run migrations** (or let FastAPI create tables on startup)
```bash
# Tables are auto-created on first run
# For production, use Alembic:
alembic upgrade head
```

7. **Seed database with listings**
```bash
# Run the existing scraper to populate listings
cd ../  # Go to project root
python main.py
```

### Running the Server

**Development mode:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Production mode:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Overview

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/register` | Register new user | No |
| POST | `/auth/login` | Login user | No |
| GET | `/auth/me` | Get current user info | Yes |

### Listings Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/listings` | Get listings with filters | Yes |
| GET | `/listings/{id}` | Get single listing | Yes |
| GET | `/listings/stats/market` | Get market statistics | Yes |
| POST | `/listings/saved-searches` | Create saved search | Yes |
| GET | `/listings/saved-searches` | Get saved searches | Yes |
| DELETE | `/listings/saved-searches/{id}` | Delete saved search | Yes |

### Subscription Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/subscriptions/create` | Create subscription | Yes |
| POST | `/subscriptions/cancel` | Cancel subscription | Yes |
| POST | `/subscriptions/reactivate` | Reactivate subscription | Yes |
| GET | `/subscriptions/portal-url` | Get billing portal URL | Yes |
| GET | `/subscriptions` | Get current subscription | Yes |
| POST | `/subscriptions/webhook` | Stripe webhook handler | No |

## Rate Limiting

Rate limits per tier (daily):
- **Free**: 10 listing views/day
- **Renter Plus**: Unlimited
- **Investor Pro**: Unlimited
- **Enterprise**: Unlimited

Rate limit logic:
1. Each `/listings/{id}` view creates `UserActivity` record
2. `check_rate_limit()` counts views for current day
3. API returns `daily_views_remaining` in responses
4. Exceeding limit returns 403 with upgrade message

## Testing

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=app --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_auth.py -v
```

### Test structure
```
tests/
├── conftest.py           # Test fixtures and config
├── test_auth.py          # Authentication tests (24 tests)
├── test_listings.py      # Listings tests (27 tests)
└── test_subscriptions.py # Subscription tests (23 tests)
```

Total: **74 tests** covering authentication, rate limiting, filtering, subscriptions, webhooks, and psychological conversion triggers.

## Database Schema

### Users Table
- Stores user accounts
- Fields: email, hashed_password, tier, is_active
- Relationships: subscription, activity, saved_searches

### Subscriptions Table
- Stores Stripe subscription data
- Fields: stripe_customer_id, stripe_subscription_id, status, tier
- One-to-one with Users

### Listings Table
- Stores rental property data
- Fields: address, price, bedrooms, bathrooms, sqft, deal_score
- Indexes on price, zip_code, bedrooms for fast filtering

### UserActivity Table
- Tracks listing views for rate limiting
- Fields: user_id, listing_id, view_date, action
- Composite index on (user_id, view_date) for fast rate limit checks

### SavedSearches Table
- Stores user's saved search filters
- Fields: user_id, name, filters (JSON), alert_frequency
- Premium feature (free tier limited to 1)

## Stripe Integration

### Setup

1. **Create products in Stripe Dashboard:**
   - Renter Plus: $14.99/month
   - Investor Pro: $199/month
   - Enterprise: $499/month

2. **Get Price IDs** from Stripe Dashboard

3. **Update .env:**
```env
STRIPE_PRICE_RENTER_PLUS=price_1234567890
STRIPE_PRICE_INVESTOR_PRO=price_0987654321
STRIPE_PRICE_ENTERPRISE=price_1122334455
```

4. **Set up webhook endpoint** in Stripe Dashboard:
   - URL: `https://your-api.com/subscriptions/webhook`
   - Events: `customer.subscription.*`, `invoice.payment_*`

### Webhook Events Handled

- `customer.subscription.created` - New subscription
- `customer.subscription.updated` - Status change
- `customer.subscription.deleted` - Cancellation
- `invoice.payment_failed` - Payment failure
- `invoice.payment_succeeded` - Successful payment

## Deployment

### Environment Setup

1. **Production environment variables:**
```env
DATABASE_URL=postgresql://user:password@prod-db:5432/nashville_rentals
SECRET_KEY=generate-secure-32-char-key
STRIPE_SECRET_KEY=sk_live_your_key
FRONTEND_URL=https://your-frontend.com
```

2. **Security settings:**
   - Use strong SECRET_KEY (32+ characters)
   - Enable HTTPS
   - Set secure CORS origins
   - Use PostgreSQL SSL mode

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

```bash
docker build -t nashville-rentals-api .
docker run -p 8000:8000 --env-file .env nashville-rentals-api
```

### Recommended Platforms

- **AWS ECS/Fargate** - Container orchestration
- **Google Cloud Run** - Serverless containers
- **DigitalOcean App Platform** - Simple deployment
- **Heroku** - Quick deployment with Postgres addon

## Theory of Mind Implementation Examples

### 1. Registration Returns Token
```python
# User doesn't have to login separately
# Immediate value = positive first impression
@router.post("/register", response_model=schemas.Token)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # ... create user ...
    access_token = auth.create_access_token(data={"sub": db_user.email})
    return schemas.Token(access_token=access_token, user=user_response)
```

### 2. Transparent Rate Limits
```python
# Show remaining views = builds trust, creates urgency
rate_limit_info = auth.check_rate_limit(db, user, today)
user_response = schemas.UserResponse(
    daily_views_remaining=rate_limit_info["remaining"]
)
```

### 3. Upgrade Messages at Friction
```python
# Clear CTA when user hits limit
if rate_limit_info["exceeded"]:
    raise HTTPException(
        status_code=403,
        detail="Daily view limit exceeded. Upgrade to see unlimited listings."
    )
```

### 4. Cancel at Period End
```python
# User keeps access until end of billing period
# Doesn't feel cheated = more likely to re-subscribe
stripe.Subscription.modify(
    subscription_id,
    cancel_at_period_end=True  # Not immediate
)
```

### 5. 7-Day Trial Period
```python
# Risk-free experience = reduces commitment anxiety
stripe_subscription = stripe.Subscription.create(
    customer=customer_id,
    items=[{"price": price_id}],
    trial_period_days=7  # Experience value first
)
```

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
pg_isready

# Test connection
psql -d nashville_rentals -U your_user
```

### Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Stripe Webhook Failures
```bash
# Test webhook locally with Stripe CLI
stripe listen --forward-to localhost:8000/subscriptions/webhook

# Verify webhook secret in .env matches Stripe Dashboard
```

### Rate Limit Not Working
```bash
# Check UserActivity records are being created
# Query database:
SELECT * FROM user_activity WHERE view_date = '20251101';

# Verify check_rate_limit() is being called
# Check logs for rate limit checks
```

## API Response Examples

### Successful Login
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "tier": "free",
    "is_active": true,
    "created_at": "2025-11-01T10:00:00Z",
    "subscription_status": null,
    "daily_views_remaining": 10
  }
}
```

### Listings Response (Free Tier)
```json
{
  "listings": [...],
  "total": 50,
  "accessible": 10,
  "page": 1,
  "page_size": 20,
  "upgrade_message": "Upgrade to see all 50 listings. You can access 10/day on free tier."
}
```

### Rate Limit Exceeded
```json
{
  "detail": "Daily view limit exceeded. Upgrade to Renter Plus for unlimited listings."
}
```

## Contributing

When adding new features, remember the Theory of Mind principles:

1. **Scarcity** - Create desire through limited access
2. **Value First** - Show value before asking for payment
3. **Transparency** - Build trust with clear limits
4. **Friction Points** - Place upgrade prompts strategically
5. **Easy Reversibility** - Make cancellation/downgrade easy

## License

Proprietary - All rights reserved

## Support

For issues or questions:
- Check logs: `tail -f logs/app.log`
- Review tests: `pytest -v`
- API docs: http://localhost:8000/docs
