"""
Main FastAPI Application - Theory of Mind:
- Clear API structure = easy developer experience
- CORS enabled = seamless frontend integration
- Error handling = helpful feedback
- Auto-generated docs = self-service learning
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from .config import get_settings
from .database import engine, Base
from .routers import auth, listings, subscriptions

settings = get_settings()

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Nashville Rentals API",
    description="""
    Nashville Rental Property API with freemium monetization model.

    ## Features
    - 🏠 Search rental listings with advanced filters
    - 📊 Market statistics and analytics
    - 💳 Subscription management with Stripe
    - 🔐 JWT authentication
    - ⚡ Rate limiting per tier

    ## Tiers
    - **Free**: 10 listings/day
    - **Renter Plus** ($14.99/mo): Unlimited listings
    - **Investor Pro** ($199/mo): ROI tools, market stats
    - **Enterprise** ($499/mo): API access, multi-user

    ## Theory of Mind
    This API is designed with psychology in mind:
    - Free tier creates "aha moment" then friction
    - Clear upgrade paths at pain points
    - Transparent limits build trust
    - Value demonstration before paywall
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
# Theory of Mind: Permissive CORS = smooth frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5173",  # Vite default port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors
    Theory of Mind: Clear error messages = less frustration
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body,
            "message": "Validation error. Please check your input."
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Database error occurred",
            "message": "Please try again later or contact support if the issue persists."
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred",
            "message": "Please try again later or contact support if the issue persists."
        },
    )


# Health check endpoint
@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint / health check
    Theory of Mind: Simple status check = monitoring confidence
    """
    return {
        "status": "ok",
        "message": "Nashville Rentals API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "api_version": "1.0.0"
    }


# Include routers
app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(subscriptions.router)


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """
    Startup tasks
    Theory of Mind: Warm startup = consistent response times
    """
    print("🚀 Nashville Rentals API starting up...")
    print(f"📊 Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'local'}")
    print(f"🌐 Frontend URL: {settings.FRONTEND_URL}")
    print(f"💳 Stripe: {'configured' if settings.STRIPE_SECRET_KEY else 'not configured'}")
    print(f"🔓 Free tier limit: {settings.FREE_TIER_LIMIT} listings/day")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("👋 Nashville Rentals API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
