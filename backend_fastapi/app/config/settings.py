from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Backend"
    PROJECT_VERSION: str = "0.1.0"

    # JWT settings
    SECRET_KEY: str = "your-super-secret-key"  # CHANGE THIS IN PRODUCTION!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Origins for CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"] # Example origins
    # Google OAuth2 settings
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None

    # MongoDB settings
    MONGODB_URI: str = "mongodb://localhost:27017/default_db"
    MONGODB_DB_NAME: str = "default_db"

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None


    class Config:
        case_sensitive = True
        env_file = ".env" # Load from .env file if present

settings = Settings()
