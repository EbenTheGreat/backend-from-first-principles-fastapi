from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENWEATHER_API_KEY: str
    CACHE_TTL_SECONDS: int = 300
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
