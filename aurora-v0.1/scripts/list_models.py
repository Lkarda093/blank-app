"""Read the account's actual Gemini model catalog; never prints secrets."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import httpx
from app.config import Settings

settings = Settings.load()
if not settings.api_key:
    raise SystemExit('Configure GEMINI_API_KEY em backend/.env primeiro.')
try:
    with httpx.Client(timeout=30) as client:
        page = None
        seen = set()
        for _ in range(30):
            response = client.get('https://generativelanguage.googleapis.com/v1beta/models',
                                  headers={'x-goog-api-key': settings.api_key},
                                  params={'pageSize': 100, **({'pageToken': page} if page else {})})
            if response.status_code != 200:
                raise SystemExit(f'Consulta recusada (HTTP {response.status_code}). Confira a chave e as permissões no AI Studio.')
            data = response.json()
            for model in data.get('models', []):
                if 'generateContent' in model.get('supportedGenerationMethods', []):
                    print(model['name'].removeprefix('models/'))
            page = data.get('nextPageToken')
            if not page or page in seen:
                break
            seen.add(page)
        print('\nEscolha um modelo de chat de TEXTO e confira seus preços/cotas no AI Studio.')
except httpx.RequestError:
    raise SystemExit('Não foi possível conectar ao Google. Verifique a rede do servidor.') from None
except (ValueError, KeyError, TypeError):
    raise SystemExit('Resposta inesperada ao listar modelos.') from None
