"""Portable, validated JSON backups. No uploaded SQL or executable payloads."""
import json
import hashlib
import hmac
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from ..auth.dependencies import require_owner
from ..database import bump_revision, connect, revision
from ..memory.routes import Preferences, read_preferences

router = APIRouter(prefix="/api/data", tags=["Dados e backups"], dependencies=[Depends(require_owner)])
MAX_BYTES = 16 * 1024 * 1024

class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")
    @field_validator("created_at", "updated_at", check_fields=False)
    @classmethod
    def valid_date(cls, value):
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("Data sem fuso horário")
        return value

class ConversationRecord(Record):
    id: UUID
    title: str = Field(min_length=1, max_length=120)
    created_at: str = Field(max_length=50)
    updated_at: str = Field(max_length=50)

class TurnRecord(Record):
    id: int = Field(ge=1, le=9223372036854775806)
    conversation_id: UUID
    request_id: UUID
    user_text: str = Field(min_length=1, max_length=8000)
    assistant_text: str = Field(min_length=1, max_length=100000)
    model: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9._-]+$")
    created_at: str = Field(max_length=50)

class Backup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["aurora-backup"]
    schema_version: Literal[2]
    exported_at: str = Field(max_length=50)
    conversations: list[ConversationRecord] = Field(max_length=10000)
    turns: list[TurnRecord] = Field(max_length=100000)
    preferences: Preferences | None

    @model_validator(mode="after")
    def valid_links(self):
        ids = {c.id for c in self.conversations}
        if len(ids) != len(self.conversations):
            raise ValueError("Conversa duplicada")
        turn_ids, requests = set(), set()
        for turn in self.turns:
            pair = (turn.conversation_id, turn.request_id)
            if turn.conversation_id not in ids or turn.id in turn_ids or pair in requests:
                raise ValueError("Troca duplicada ou sem conversa")
            turn_ids.add(turn.id)
            requests.add(pair)
        return self

def snapshot(db):
    return {"format": "aurora-backup", "schema_version": 2,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "conversations": [dict(r) for r in db.execute("SELECT * FROM conversations ORDER BY created_at,id")],
            "turns": [dict(r) for r in db.execute("SELECT * FROM turns ORDER BY id")],
            "preferences": read_preferences(db)}

def encode_backup(data):
    try:
        data = Backup.model_validate(data).model_dump(mode="json")
        content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    except (ValueError, UnicodeError):
        raise HTTPException(422, "Dados fora dos limites do backup JSON. Preserve o banco SQLite conforme o README.") from None
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "Backup acima de 16 MiB. Use a cópia manual do SQLite descrita no README.")
    return content

async def parse_backup(request):
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BYTES:
            raise HTTPException(413, "O backup deve ter no máximo 16 MiB.")
        chunks.append(chunk)
    try:
        return Backup.model_validate_json(b"".join(chunks))
    except (ValueError, UnicodeError):
        raise HTTPException(422, "Arquivo inválido. Selecione um backup JSON completo exportado pela Aurora 0.2.") from None

def preview_ticket(data, current_revision, owner_token):
    digest = hashlib.sha256(data.model_dump_json().encode()).hexdigest()
    return hmac.new(owner_token.encode(), f"{current_revision}:{digest}".encode(), hashlib.sha256).hexdigest()

def download(content, filename, media_type="application/json"):
    return Response(content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})

@router.get("/backup")
def backup(request: Request):
    with connect(request.app.state.settings.database) as db:
        db.execute("BEGIN")
        content = encode_backup(snapshot(db))
    return download(content, "aurora-backup.json")

@router.get("/stats")
def stats(request: Request):
    with connect(request.app.state.settings.database) as db:
        db.execute("BEGIN")
        return {"conversations": db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0],
                "turns": db.execute("SELECT COUNT(*) FROM turns").fetchone()[0],
                "preferences_saved": read_preferences(db) is not None, "revision": revision(db)}

@router.post("/restore/preview")
async def preview(request: Request):
    data = await parse_backup(request)
    with connect(request.app.state.settings.database) as db:
        db.execute("BEGIN")
        current = {"conversations": db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0],
                   "turns": db.execute("SELECT COUNT(*) FROM turns").fetchone()[0]}
        current_revision = revision(db)
    return {"conversations": len(data.conversations), "turns": len(data.turns),
            "preferences": data.preferences.model_dump() if data.preferences else None,
            "expected_revision": current_revision, "current": current,
            "ticket": preview_ticket(data, current_revision, request.app.state.settings.owner_token)}

@router.post("/restore")
async def restore(request: Request):
    if request.headers.get("X-Aurora-Confirm") != "RESTAURAR":
        raise HTTPException(400, "Digite RESTAURAR para confirmar a substituição dos dados.")
    raw_revision = request.headers.get("X-Aurora-Revision", "")
    if not raw_revision.isdigit() or len(raw_revision) > 18:
        raise HTTPException(400, "Confira a prévia antes de restaurar.")
    data = await parse_backup(request)
    ticket = request.headers.get("X-Aurora-Preview", "")
    expected = preview_ticket(data, int(raw_revision), request.app.state.settings.owner_token)
    if not hmac.compare_digest(ticket.encode(), expected.encode()):
        raise HTTPException(409, "O arquivo mudou ou a prévia expirou. Analise o backup novamente.")
    if data.preferences and request.headers.get("X-Aurora-Preferences-Consent") != "1":
        raise HTTPException(400, "Autorize explicitamente o uso das preferências presentes no backup.")
    state = request.app.state
    if state.send_lock.locked():
        raise HTTPException(409, "Aguarde a resposta ou operação em andamento antes de restaurar.")
    async with state.send_lock:
        with connect(state.settings.database) as db:
            db.execute("BEGIN IMMEDIATE")
            if revision(db) != int(raw_revision):
                raise HTTPException(409, "Os dados mudaram desde a prévia. Selecione o arquivo novamente e confira os números.")
            recovery = encode_backup(snapshot(db))
            folder = state.settings.database.parent / "backups"
            folder.mkdir(mode=0o700, exist_ok=True)
            recovery_id = str(uuid4())
            file = folder / f"before-restore-{recovery_id}.json"
            # Failure to write/flush recovery aborts the transaction before deletion.
            import os
            descriptor = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as output:
                output.write(recovery)
                output.flush()
                os.fsync(output.fileno())
            db.execute("DELETE FROM conversations")
            db.execute("DELETE FROM preferences")
            for c in data.conversations:
                db.execute("INSERT INTO conversations VALUES(?,?,?,?)", (str(c.id), c.title, c.created_at, c.updated_at))
            for t in data.turns:
                db.execute("INSERT INTO turns VALUES(?,?,?,?,?,?,?)", (t.id, str(t.conversation_id), str(t.request_id), t.user_text, t.assistant_text, t.model, t.created_at))
            if data.preferences:
                p = data.preferences
                db.execute("INSERT INTO preferences VALUES(1,?,?,?)", (p.name, p.response_style, p.notes))
            bump_revision(db)
    return {"restored": True, "recovery_id": recovery_id}

@router.get("/recovery")
def recovery_list(request: Request):
    folder = request.app.state.settings.database.parent / "backups"
    result = []
    for file in folder.glob("before-restore-*.json"):
        match = re.fullmatch(r"before-restore-([a-f0-9-]{36})\.json", file.name)
        if match and not file.is_symlink():
            result.append({"id": match[1], "created_at": datetime.fromtimestamp(file.stat().st_mtime, timezone.utc).isoformat()})
    return sorted(result, key=lambda item: item["created_at"], reverse=True)[:20]

@router.get("/recovery/{recovery_id}")
def recovery_download(recovery_id: UUID, request: Request):
    file = request.app.state.settings.database.parent / "backups" / f"before-restore-{recovery_id}.json"
    if not file.is_file() or file.is_symlink():
        raise HTTPException(404, "Cópia de segurança não encontrada.")
    return download(file.read_bytes(), f"aurora-antes-restauracao-{recovery_id}.json")
