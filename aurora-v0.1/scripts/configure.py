"""Interactive first-run setup. Never overwrites an existing .env."""
from getpass import getpass
from pathlib import Path
import re
import secrets

root = Path(__file__).resolve().parents[1]
path = root / 'backend' / '.env'
if path.exists():
    raise SystemExit('backend/.env já existe. Edite-o manualmente; nenhuma configuração foi alterada.')
print('A chave Gemini é digitada sem aparecer. Enter permite configurar depois.')
key = getpass('Chave Gemini: ').strip()
if key and not re.fullmatch(r'[A-Za-z0-9_-]+', key):
    raise SystemExit('Formato de chave inesperado. Nenhum arquivo foi criado.')
print('Informe um identificador de modelo de texto disponível na sua conta do Google AI Studio.')
print('Enter deixa o chat desabilitado até você preencher GEMINI_MODELS no arquivo .env.')
model = input('Modelo Gemini: ').strip()
if model and not re.fullmatch(r'[A-Za-z0-9._-]{1,100}', model):
    raise SystemExit('Identificador inválido. Nenhum arquivo foi criado.')
with path.open('x') as file:
    file.write(f'GEMINI_API_KEY={key}\nGEMINI_MODELS={model}\nAURORA_OWNER_TOKEN={secrets.token_urlsafe(32)}\nAURORA_DB_PATH=data/aurora.sqlite3\n')
path.chmod(0o600)
print('Configuração criada. Abra backend/.env no editor e copie AURORA_OWNER_TOKEN para entrar na interface.')
print('Não compartilhe esse arquivo ou seu conteúdo.')
