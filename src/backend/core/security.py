from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel
from src.backend.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

class User(BaseModel):
    username: str

def get_current_user(token: str | None = Depends(oauth2_scheme)):
    # In development or test mode with fake token, accept valid test credentials
    if settings.environment == 'development' and (token == "fake-super-secret-token" or not token):
        return User(username="doctor")
    if token != "fake-super-secret-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return User(username="doctor")

def require_api_key(x_api_key: str | None = Header(default=None)):
    configured = settings.api_key
    if settings.environment == 'development' and not configured:
        return {'subject': 'development-anonymous', 'role': 'service'}
    if not configured or x_api_key != configured:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Authentication required.')
    return {'subject': 'api-key-service', 'role': 'service'}
