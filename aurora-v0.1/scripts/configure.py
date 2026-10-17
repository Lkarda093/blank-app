"""Legacy web setup: public settings only; no key is ever written to .env."""
from getpass import getpass
import os
from pathlib import Path
import re
import secrets
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'backend'))


def is_windows():
    return os.name == 'nt'


def main():
    from app.cloud_policy import CLOUD_NOTICE
    from app.credentials import CredentialError, WindowsCredentialStore
    path = root / 'backend' / '.env'
    if path.exists():
        raise SystemExit('backend/.env já existe. Nenhum arquivo foi alterado. Para desktop, use Configurar-Aurora.cmd; não grave chaves em .env.')
    print(CLOUD_NOTICE)
    if input('Para autorizar o uso de nuvem, digite ACEITO: ').strip() != 'ACEITO':
        raise SystemExit('Configuração cancelada. Nada foi salvo.')
    model = input('Identificador do modelo de texto Gemini na sua conta: ').strip()
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,100}', model):
        raise SystemExit('Identificador inválido. Nenhum arquivo foi criado.')
    if is_windows():
        try:
            store = WindowsCredentialStore()
            key = getpass('Chave Gemini (Enter mantém a chave do cofre): ').strip()
            if key:
                store.write(key)
            elif not store.read():
                raise CredentialError('Cadastre uma chave no cofre antes de continuar.')
            key = ''
        except CredentialError as exc:
            raise SystemExit(str(exc)) from None
    else:
        print('No servidor, configure GEMINI_API_KEY no gerenciador de segredos do ambiente. Não coloque a chave em arquivo ou comando no histórico do terminal.')
    with path.open('x', encoding='utf-8') as file:
        file.write(f'GEMINI_MODELS={model}\nAURORA_OWNER_TOKEN={secrets.token_urlsafe(32)}\nAURORA_DB_PATH=data/aurora.sqlite3\n')
    path.chmod(0o600)
    print('Configuração web criada sem chave de API. O token de acesso está em backend/.env; não compartilhe esse arquivo.')


if __name__ == '__main__':
    main()
