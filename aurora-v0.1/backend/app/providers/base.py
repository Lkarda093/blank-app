from typing import Protocol

class ProviderError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)

class Provider(Protocol):
    async def generate(self, model: str, messages: list[dict], personalization: str = "") -> str: ...
