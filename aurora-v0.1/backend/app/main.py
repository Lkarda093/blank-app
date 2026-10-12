import asyncio
import logging
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .config import Settings
from .database import initialize
from .conversations.routes import router
from .providers.gemini import GeminiProvider
from .auth.routes import router as auth_router
from .memory.routes import router as memory_router
from .data.routes import router as data_router


def create_app(settings: Settings | None = None, provider=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.settings = settings or Settings.load()
        initialize(app.state.settings.database)
        app.state.send_lock = asyncio.Lock()
        app.state.login_failures = []
        async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=10), follow_redirects=False) as client:
            app.state.provider = provider or GeminiProvider(client, app.state.settings.api_key)
            yield

    app = FastAPI(title="Aurora API", version="0.3.0", lifespan=lifespan,
                  description="API pessoal. Use Authorize com o token do proprietário. Um único processo/worker.")
    app.include_router(router)
    app.include_router(auth_router)
    app.include_router(memory_router)
    app.include_router(data_router)

    @app.middleware("http")
    async def headers(request: Request, call_next):
        # Same-origin proxy. Cookie mutations require a custom header and matching Origin.
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return JSONResponse(status_code=422, content={"detail": "Dados inválidos. Confira os campos e seus limites; mensagens aceitam até 8.000 caracteres."})

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        # Never log prompts, tokens, upstream bodies or exception strings.
        logging.getLogger("aurora").error("Falha interna: %s", type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Erro interno. Consulte o terminal do servidor. Sua mensagem pode ser reenviada com o mesmo identificador."})

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.3.0"}

    return app

app = create_app()
