from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

from app.config import settings


connect_args = {}
if settings.database_url.startswith("sqlite"):
    # SQLite requires this for FastAPI's multi-threaded request handling
    connect_args = {"check_same_thread": False}

# To switch to PostgreSQL, change DATABASE_URL in .env to:
#   postgresql://user:password@localhost:5432/reflection_buddy
# No other code changes needed — SQLAlchemy handles the rest.
engine = create_engine(settings.database_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: yields a database session and ensures cleanup."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
