import secrets
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)

def require_owner(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None or not secrets.compare_digest(credentials.credentials.encode(), request.app.state.settings.owner_token.encode()):
        raise HTTPException(401, "Token do proprietário inválido ou ausente.", headers={"WWW-Authenticate": "Bearer"})
