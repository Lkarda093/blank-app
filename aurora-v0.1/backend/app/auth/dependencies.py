import hashlib
import hmac
import secrets
import time
from urllib.parse import urlsplit
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ..database import connect

COOKIE = "aurora_session"
bearer = HTTPBearer(auto_error=False)

def session_digest(value, owner_token):
    return hmac.new(owner_token.encode(), value.encode(), hashlib.sha256).hexdigest()

def check_browser_write(request: Request):
    if request.headers.get("X-Aurora-Request") != "1":
        raise HTTPException(403, "Solicitação inválida. Use a interface da Aurora.")
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).netloc != request.headers.get("host"):
        raise HTTPException(403, "Origem da solicitação não autorizada.")

def secure_cookie(request):
    # Public Codespaces URLs use HTTPS even behind the local Vite proxy.
    return request.url.scheme == "https" or request.url.hostname not in {"localhost", "127.0.0.1", "::1", "testserver"}

def require_owner(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    settings = request.app.state.settings
    if credentials:
        if secrets.compare_digest(credentials.credentials.encode(), settings.owner_token.encode()):
            return
        raise HTTPException(401, "Token do proprietário inválido.")
    value = request.cookies.get(COOKIE, "")
    if value and len(value) <= 256:
        digest = session_digest(value, settings.owner_token)
        with connect(settings.database) as db:
            valid = db.execute("SELECT 1 FROM sessions WHERE digest=? AND expires_at>?", (digest, int(time.time()))).fetchone()
        if valid:
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                check_browser_write(request)
            return
    raise HTTPException(401, "Sua sessão expirou. Entre com o token do proprietário.", headers={"WWW-Authenticate": "Bearer"})
