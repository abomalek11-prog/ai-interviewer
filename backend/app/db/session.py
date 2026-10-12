from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# pool_recycle: serverless Postgres (Neon) drops idle connections after a few minutes;
# recycling earlier avoids handing a dead connection to a request.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_recycle=240)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
