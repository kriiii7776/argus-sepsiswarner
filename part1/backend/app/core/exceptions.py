"""
Custom exception classes and global error handlers conforming to APIErrorResponse.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.schemas.contract import APIErrorPayload, APIErrorResponse
from app.core.logging import logger


class ARGUSException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


async def argus_exception_handler(request: Request, exc: ARGUSException) -> JSONResponse:
    logger.error(f"ARGUSException [{exc.code}]: {exc.message} - path: {request.url.path}")
    error_payload = APIErrorResponse(
        error=APIErrorPayload(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            timestamp=datetime.now(timezone.utc),
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload.model_dump(mode="json"),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning(f"ValidationError on path {request.url.path}: {exc.errors()}")
    error_payload = APIErrorResponse(
        error=APIErrorPayload(
            code="VALIDATION_ERROR",
            message="Request payload failed contract validation.",
            details={"errors": exc.errors()},
            timestamp=datetime.now(timezone.utc),
        )
    )
    return JSONResponse(
        status_code=422,
        content=error_payload.model_dump(mode="json"),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled Exception: {str(exc)} - path: {request.url.path}", exc_info=True)
    error_payload = APIErrorResponse(
        error=APIErrorPayload(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred.",
            details={"error": str(exc)} if settings_debug_enabled() else None,
            timestamp=datetime.now(timezone.utc),
        )
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload.model_dump(mode="json"),
    )


def settings_debug_enabled() -> bool:
    from app.core.config import settings
    return settings.DEBUG
