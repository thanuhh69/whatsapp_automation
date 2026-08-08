from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.config import settings

security = HTTPBearer(auto_error=False)

def verify_bearer_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    expected_token = settings.API_TOKEN.strip()
    if not expected_token:
        return True # If token not yet set, allow (will be initialized on run)
    
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token required (Bearer <token>)"
        )
    if credentials.credentials != expected_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Bearer Token"
        )
    return True
