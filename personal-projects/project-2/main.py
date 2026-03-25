from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from routes import v1
from db import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup — runs once before the server starts accepting requests."""
    create_db_and_tables()
    yield


app = FastAPI(
    title="Weather Bookmark API",
    description="API for managing weather bookmarks and weather data",
    lifespan=lifespan
)

app.include_router(v1)


@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    return {"message": "Welcome to the Weather Bookmark API"}
