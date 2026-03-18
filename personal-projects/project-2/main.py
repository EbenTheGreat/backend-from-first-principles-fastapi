from fastapi import FastAPI, status
from routes import v1


app = FastAPI(title="Weather Bookmark API", description="API for managing weather bookmarks and weather data")

app.include_router(v1)


@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    return {"message": "Welcome to the Weather Bookmark API"}
