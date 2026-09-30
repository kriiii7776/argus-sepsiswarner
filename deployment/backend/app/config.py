from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = 'sqlite:///./sepsisguard.db'
    api_key: str | None = None
    environment: str = 'development'
    cors_origins: str = 'http://localhost:5173'
    max_vitals_per_request: int = Field(default=100, ge=1, le=1000)
    class Config: env_file = '.env'; extra = 'ignore'

@lru_cache
def settings(): return Settings()
