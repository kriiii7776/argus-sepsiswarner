from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ARGUS SepsisGuard AI Backend"
    SECRET_KEY: str = "supersecretkey_please_change_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    MODEL_VERSION: str = "1.0.0"

    database_url: str = 'sqlite:///./sepsisguard.db'
    api_key: str | None = None
    environment: str = 'development'
    cors_origins: str = 'http://localhost:5173,http://localhost:3000'
    max_vitals_per_request: int = Field(default=100, ge=1, le=1000)

    argus_part1_ws_url: str = Field(default="ws://127.0.0.1:8001/api/v1/stream", validation_alias="ARGUS_PART1_WS_URL")
    argus_part1_bridge_enabled: bool = Field(default=False, validation_alias="ARGUS_PART1_BRIDGE_ENABLED")

    @property
    def ARGUS_PART1_WS_URL(self) -> str:
        return self.argus_part1_ws_url

    @property
    def ARGUS_PART1_BRIDGE_ENABLED(self) -> bool:
        return self.argus_part1_bridge_enabled

    class Config:
        case_sensitive = False
        env_file = '.env'
        extra = 'ignore'

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = Settings()
