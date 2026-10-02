"""
Application configuration management for ARGUS Simulator.
"""

import os
from typing import List
from pydantic import BaseModel, Field


class Settings(BaseModel):
    PROJECT_NAME: str = Field(default="ARGUS Data Source & Simulation Platform")
    VERSION: str = Field(default="1.0.0")
    API_V1_STR: str = Field(default="/api/v1")
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="INFO")
    
    # Host & Port
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    # Database Configuration (PostgreSQL with SQLite fallback)
    DATABASE_URL: str = Field(default="postgresql://argus:argus_pass@localhost:5432/argus_db")
    DB_POOL_SIZE: int = Field(default=5)
    DB_MAX_OVERFLOW: int = Field(default=10)

    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(default=["*"])

    # Demo Mode Configuration
    DEMO_MODE: bool = Field(default=False)
    DEMO_PATIENT_ID: str = Field(default="PATIENT-001")
    DEMO_SPEED_FACTOR: float = Field(default=1.0)

    @classmethod
    def load_from_env(cls) -> "Settings":
        return cls(
            PROJECT_NAME=os.getenv("ARGUS_PROJECT_NAME", "ARGUS Data Source & Simulation Platform"),
            VERSION=os.getenv("ARGUS_VERSION", "1.0.0"),
            API_V1_STR=os.getenv("ARGUS_API_V1_STR", "/api/v1"),
            ENVIRONMENT=os.getenv("ARGUS_ENV", "development"),
            DEBUG=os.getenv("ARGUS_DEBUG", "true").lower() in ("true", "1", "yes"),
            LOG_LEVEL=os.getenv("ARGUS_LOG_LEVEL", "INFO"),
            HOST=os.getenv("ARGUS_HOST", "0.0.0.0"),
            PORT=int(os.getenv("ARGUS_PORT", "8000")),
            DATABASE_URL=os.getenv("ARGUS_DATABASE_URL", os.getenv("DATABASE_URL", "postgresql://argus:argus_pass@localhost:5432/argus_db")),
            DB_POOL_SIZE=int(os.getenv("ARGUS_DB_POOL_SIZE", "5")),
            DB_MAX_OVERFLOW=int(os.getenv("ARGUS_DB_MAX_OVERFLOW", "10")),
            DEMO_MODE=os.getenv("ARGUS_DEMO_MODE", "false").lower() in ("true", "1", "yes"),
            DEMO_PATIENT_ID=os.getenv("ARGUS_DEMO_PATIENT_ID", "PATIENT-001"),
            DEMO_SPEED_FACTOR=float(os.getenv("ARGUS_DEMO_SPEED", os.getenv("DEMO_SPEED", "1.0"))),
        )



settings = Settings.load_from_env()
