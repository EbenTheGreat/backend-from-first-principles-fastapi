from typing import Annotated
from fastapi import Depends
from sqlmodel import SQLModel, Session, create_engine

# SQLite database file — persists in the project folder
sqlite_url = "sqlite:///bookmarks.db"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})


def create_db_and_tables():
    """Create all SQLModel table models in the database on startup."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency — yields one Session per request, closes automatically."""
    with Session(engine) as session:
        yield session


# Reusable type alias — inject into route params instead of using Depends() each time
SessionDep = Annotated[Session, Depends(get_session)]
