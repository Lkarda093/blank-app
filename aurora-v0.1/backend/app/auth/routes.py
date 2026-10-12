import secrets
import time
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from .dependencies import COOKIE, check_browser_write, require_owner, secure_cookie, session_digest
from ..database import connect

router = APIRouter(prefix="/api/auth", tags=["Acesso"])

class Login(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    remember: bool = False

@router.post("/login")
async def login(payload: Login, request: Request, response: Response):
    check_browser_write(request)
    state = request.app.state
    now = int(time.time())
    state.login_failures[:] = [t for t in state.login_failures if t > now - 60]
    if len(state.login_failures) >= 5:
        raise HTTPException(429, "Muitas tentativas de entrada. Aguarde um minuto.")
    if not secrets.compare_digest(payload.token.encode(), state.settings.owner_token.encode()):
        state.login_failures.append(now)
        raise HTTPException(401, "Token do proprietário inválido.")
    value = secrets.token_urlsafe(32)
    ttl = 7 * 86400 if payload.remember else 12 * 3600
    with connect(state.settings.database) as db:
        db.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
        previous = request.cookies.get(COOKIE)
        if previous:
            db.execute("DELETE FROM sessions WHERE digest=?", (session_digest(previous, state.settings.owner_token),))
        db.execute("INSERT INTO sessions VALUES (?,?)", (session_digest(value, state.settings.owner_token), now + ttl))
    response.set_cookie(COOKIE, value, max_age=ttl if payload.remember else None, httponly=True,
                        secure=secure_cookie(request), samesite="strict", path="/api")
    return {"authenticated": True, "expires_at": now + ttl}

@router.get("/session", dependencies=[Depends(require_owner)])
def session():
    return {"authenticated": True}

@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response):
    # Logout also works for an expired session, but still requires the browser header.
    check_browser_write(request)
    value = request.cookies.get(COOKIE)
    if value:
        with connect(request.app.state.settings.database) as db:
            db.execute("DELETE FROM sessions WHERE digest=?", (session_digest(value, request.app.state.settings.owner_token),))
    response.delete_cookie(COOKIE, path="/api", httponly=True, secure=secure_cookie(request), samesite="strict")
