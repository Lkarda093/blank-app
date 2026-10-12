"""Test-only application. DO NOT use this as the normal backend."""
import os
from pathlib import Path
from app.config import Settings
from app.main import create_app
from app.providers.base import ProviderError

class BrowserTestProvider:
    async def generate(self, model, messages, personalization=""):
        if messages[-1]['content'] == 'test-quota':
            raise ProviderError(429, 'Cota simulada para teste de interface.')
        return 'RESPOSTA SIMULADA DE TESTE: ' + messages[-1]['content']

def app_factory():
    path = os.environ.get('AURORA_E2E_DB')
    if not path:
        raise RuntimeError('Defina AURORA_E2E_DB para um banco temporário de testes.')
    return create_app(Settings('browser-test-owner-token-0000000000000000', 'fake-key', ('test-model',), Path(path)), BrowserTestProvider())
