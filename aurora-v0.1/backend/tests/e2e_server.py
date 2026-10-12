"""Test-only application. DO NOT use this as the normal backend."""
import os
from pathlib import Path
from app.config import Settings
from app.main import create_app
from app.providers.base import ProviderError

class BrowserTestProvider:
    async def generate(self, model, messages, personalization=""):
        if messages[-1]['content'] == 'test-auto-fallback' and model == 'test-model':
            raise ProviderError(429, 'Cota simulada do modelo principal.')
        if messages[-1]['content'] == 'test-quota':
            raise ProviderError(429, 'Cota simulada para teste de interface.')
        text=messages[-1]['content']
        if 'DOCUMENTOS SELECIONADOS' in text:
            question=text.split('\n\nDOCUMENTOS SELECIONADOS')[0]
            if question=='Use somente o PDF' and 'TXT_NOT_SELECTED_CHECK' in text:
                raise ProviderError(422,'Um documento não selecionado foi enviado.')
            page=2 if '"page": 2' in text else 1
            return 'RESPOSTA SIMULADA DE TESTE: '+question+f' [D1 p. {page}]'
        return 'RESPOSTA SIMULADA DE TESTE: ' + text

def app_factory():
    path = os.environ.get('AURORA_E2E_DB')
    if not path:
        raise RuntimeError('Defina AURORA_E2E_DB para um banco temporário de testes.')
    return create_app(Settings('browser-test-owner-token-0000000000000000', 'fake-key', ('test-model','test-alternate'), Path(path), ('test-model','test-alternate')), BrowserTestProvider())
