from typing import Annotated
from fastapi import Depends
from sqlmodel import SQLModel, Session, create_engine
from config import settings

# ─────────────────────────────────────────────
# Supabase PostgreSQL connection
# The DATABASE_URL is loaded from .env — never hardcode credentials here.
# Format: postgresql+psycopg2://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
# ─────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,          # Set echo=True temporarily to log raw SQL for debugging
    pool_pre_ping=True,  # Checks connection health before use — avoids stale connection errors
)


def create_db_and_tables():
    """Create all SQLModel table models in the Supabase database on startup."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency — yields one Session per request, closes automatically."""
    with Session(engine) as session:
        yield session


# Reusable type alias — inject into route params instead of using Depends() each time
SessionDep = Annotated[Session, Depends(get_session)]
