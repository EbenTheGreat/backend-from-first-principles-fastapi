from fastapi import FastAPI
from routes import v1

app = FastAPI(
    title="task-manager-api",
    description="CRUD api for managing tasks",
    version="1.0.0"
)

app.include_router(v1)



