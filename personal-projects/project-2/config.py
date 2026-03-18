from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    OPENWEATHER_API_KEY: str
    CACHE_TTL_SECONDS: int = 300
    
    class Config:
        env_file = Path(__file__).parent / ".env"
        env_file_encoding = "utf-8"

settings = Settings()
