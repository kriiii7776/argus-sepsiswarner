from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.backend.core.config import settings
from src.backend.api.router import api_router
from src.backend.core.logging import logger

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Argus Backend")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Argus Backend")
