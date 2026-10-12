from typing import Protocol

class ProviderError(Exception):
    def __init__(self, status: int, message: str, *, upstream_status: int | None = None):
        self.status = status
        self.message = message
        self.upstream_status = upstream_status
        super().__init__(message)

class Provider(Protocol):
    async def generate(self, model: str, messages: list[dict], personalization: str = "") -> str: ...
