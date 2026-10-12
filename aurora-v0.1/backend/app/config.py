"""Server-only configuration; paths are independent of the launch directory."""
import os
import re
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Settings:
    owner_token: str
    api_key: str = ""
    models: tuple[str, ...] = ()
    database: Path = ROOT / "data" / "aurora.sqlite3"

    free_fallback_models: tuple[str, ...] = ()

    @classmethod
    def load(cls):
        load_dotenv(ROOT / ".env")
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
        return cls(token, os.getenv("GEMINI_API_KEY", ""), models, path if path.is_absolute() else ROOT / path, fallback)
