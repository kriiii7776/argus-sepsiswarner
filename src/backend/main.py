from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.backend.core.config import settings
from src.backend.api.router import api_router
from src.backend.core.logging import logger
from src.backend.db.store import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Argus SepsisGuard Backend")
    init_db()
    logger.info("Database tables initialized")
    yield
    logger.info("Shutting down Argus SepsisGuard Backend")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Canonical API Router (/api/v1)
app.include_router(api_router, prefix=settings.API_V1_STR)

# Legacy / Unprefixed Compatibility Routers (for smooth transitional support)
app.include_router(api_router)
