"""
Database setup - Theory of Mind:
- SQLAlchemy ORM = type-safe, prevents SQL injection
- Connection pooling = fast response times
- Async support = handle many concurrent users
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use
    pool_size=10,  # Support concurrent users
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for route handlers"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
