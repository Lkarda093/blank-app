"""Server-only configuration; paths are independent of the launch directory."""
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import dotenv_values, load_dotenv
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def is_windows():
    return os.name == 'nt'


def load_gemini_key():
    if dotenv_values(ROOT / '.env').get('GEMINI_API_KEY'):
        raise ValueError('Remova GEMINI_API_KEY de backend/.env. Chaves não podem ficar em arquivo.')
    if is_windows():
        from .credentials import WindowsCredentialStore
        return WindowsCredentialStore().read() or ''
    return os.getenv('GEMINI_API_KEY', '')

@dataclass(frozen=True)
class Settings:
    owner_token: str = field(repr=False)
    api_key: str = field(default="", repr=False)
    models: tuple[str, ...] = ()
    database: Path = ROOT / "data" / "aurora.sqlite3"

    free_fallback_models: tuple[str, ...] = ()
    provider: str = "gemini"
    local_url: str = "http://127.0.0.1:11434"

    def __post_init__(self):
        if self.provider not in {"gemini", "ollama", "llamacpp"}:
            raise ValueError("Provedor inválido: use gemini, ollama ou llamacpp.")
        u = urlsplit(self.local_url)
        if u.scheme != "http" or u.hostname not in {"127.0.0.1", "localhost", "::1"} or u.username or u.password or u.query or u.fragment or u.path not in {"", "/"}:
            raise ValueError("O motor local deve usar HTTP no próprio computador, sem caminho ou credenciais.")
        if self.provider != "gemini" and self.free_fallback_models:
            raise ValueError("O modo local não admite troca automática para a nuvem.")

    @classmethod
    def load(cls):
        # Refuse the disk-backed key before dotenv could copy it to the environment.
        if dotenv_values(ROOT / '.env').get('GEMINI_API_KEY'):
            raise ValueError('Remova GEMINI_API_KEY de backend/.env. Use o cofre do Windows ou um segredo do ambiente no servidor. Nenhuma chave foi movida ou apagada automaticamente.')
        load_dotenv(ROOT / ".env")
        provider = os.getenv("AURORA_PROVIDER", "gemini")
        if provider != "gemini":
            token = os.getenv("AURORA_OWNER_TOKEN", "")
            if len(token) < 32:
                raise ValueError("Configure AURORA_OWNER_TOKEN com pelo menos 32 caracteres.")
            models = tuple(m.strip() for m in os.getenv("AURORA_LOCAL_MODELS", "llama3.2:1b" if provider == "ollama" else "aurora-local").split(",") if m.strip())
            if not models or any(not re.fullmatch(r"[a-zA-Z0-9._:/-]{1,100}", m) for m in models):
                raise ValueError("Configure identificadores válidos em AURORA_LOCAL_MODELS.")
            path = Path(os.getenv("AURORA_DB_PATH", "data/aurora.sqlite3"))
            return cls(token, models=models, database=path if path.is_absolute() else ROOT / path,
                       provider=provider, local_url=os.getenv("AURORA_LOCAL_URL", "http://127.0.0.1:11434" if provider == "ollama" else "http://127.0.0.1:8080"))
        models = tuple(dict.fromkeys(m.strip() for m in os.getenv("GEMINI_MODELS", "").split(",") if m.strip()))
        if any(not re.fullmatch(r"[a-zA-Z0-9._-]{1,100}", m) for m in models):
            raise ValueError("GEMINI_MODELS contém um identificador inválido.")
        fallback = tuple(dict.fromkeys(m.strip() for m in os.getenv("GEMINI_FREE_FALLBACK_MODELS", "").split(",") if m.strip()))
        if any(m not in models for m in fallback):
            raise ValueError("GEMINI_FREE_FALLBACK_MODELS deve conter somente modelos autorizados em GEMINI_MODELS.")
        token = os.getenv("AURORA_OWNER_TOKEN", "")
        if len(token) < 32:
            raise ValueError("Configure AURORA_OWNER_TOKEN com pelo menos 32 caracteres em backend/.env.")
        path = Path(os.getenv("AURORA_DB_PATH", "data/aurora.sqlite3"))
        return cls(token, load_gemini_key(), models, path if path.is_absolute() else ROOT / path, fallback)
