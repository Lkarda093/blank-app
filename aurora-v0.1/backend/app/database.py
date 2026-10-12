import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
import os

@contextmanager
def connect(path: Path):
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.create_function("casefold", 1, lambda value: value.casefold(), deterministic=True)
    db.execute("PRAGMA foreign_keys = ON")
    try:
        with db:
            yield db
    finally:
        db.close()

def bump_revision(db):
    db.execute("UPDATE metadata SET value=CAST(value AS INTEGER)+1 WHERE key='data_revision'")

def revision(db):
    return int(db.execute("SELECT value FROM metadata WHERE key='data_revision'").fetchone()[0])

def initialize(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version > 3:
            raise RuntimeError("Banco de uma versão mais nova. Não faça downgrade sem restaurar um backup compatível.")
        if version in (1, 2):
            folder = path.parent / "backups"
            folder.mkdir(mode=0o700, exist_ok=True)
            backup_path = folder / f"before-upgrade-v0.4-{uuid4()}.sqlite3"
            descriptor = os.open(backup_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(descriptor)
            target = sqlite3.connect(backup_path)
            try:
                db.backup(target)
            finally:
                target.close()
        db.execute("PRAGMA journal_mode = WAL")
        db.executescript('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            request_id TEXT NOT NULL,
            user_text TEXT NOT NULL,
            assistant_text TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(conversation_id, request_id)
        );
        CREATE INDEX IF NOT EXISTS turns_conversation ON turns(conversation_id, id);
        ''')
        db.execute("CREATE TABLE IF NOT EXISTS request_origins (turn_id INTEGER PRIMARY KEY REFERENCES turns(id) ON DELETE CASCADE, requested_model TEXT NOT NULL)")
        # Transactional, additive migration: existing conversation/turn columns stay intact.
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("INSERT OR IGNORE INTO metadata VALUES ('data_revision','0')")
        db.execute("CREATE TABLE IF NOT EXISTS preferences (id INTEGER PRIMARY KEY CHECK(id=1), name TEXT NOT NULL, response_style TEXT NOT NULL, notes TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS sessions (digest TEXT PRIMARY KEY, expires_at INTEGER NOT NULL)")
        db.execute("""CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('pdf','txt')),
            size_bytes INTEGER NOT NULL, sha256 TEXT NOT NULL UNIQUE, original BLOB NOT NULL,
            pages_json TEXT NOT NULL, page_count INTEGER NOT NULL, char_count INTEGER NOT NULL,
            created_at TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS conversation_documents (
            conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            PRIMARY KEY(conversation_id,document_id))""")
        db.execute("""CREATE TABLE IF NOT EXISTS turn_document_context (
            turn_id INTEGER PRIMARY KEY REFERENCES turns(id) ON DELETE CASCADE,
            request_json TEXT NOT NULL, documents_json TEXT NOT NULL,
            sources_json TEXT NOT NULL, warning TEXT NOT NULL)""")
        db.execute("PRAGMA user_version = 3")
    path.chmod(0o600)
