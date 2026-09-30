"""Authentication boundary; replace development API-key logic with OIDC/JWT verification in deployment."""
from fastapi import Header, HTTPException, status
from .config import settings

def require_api_key(x_api_key: str | None = Header(default=None)):
    configured = settings().api_key
    if settings().environment == 'development' and not configured:
        return {'subject':'development-anonymous','role':'service'}
    if not configured or x_api_key != configured:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Authentication required.')
    return {'subject':'api-key-service','role':'service'}
