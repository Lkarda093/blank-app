import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from ..auth.dependencies import require_owner
from ..database import connect
from ..providers.base import ProviderError

router = APIRouter(prefix="/api", dependencies=[Depends(require_owner)])

def now():
    return datetime.now(timezone.utc).isoformat()

def require_conversation(db, cid):
    row = db.execute("SELECT * FROM conversations WHERE id=?", (str(cid),)).fetchone()
    if row is None:
        raise HTTPException(404, "Conversa não encontrada.")
    return dict(row)

def messages_from_turns(turns):
    messages = []
    for t in turns:
        for role in ("user", "assistant"):
            messages.append({"id": f'{t["id"]}-{role}', "role": role, "content": t[f"{role}_text"], "created_at": t["created_at"], "model": t["model"]})
    return messages

class SendMessage(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    model: str = Field(min_length=1, max_length=100)
    request_id: UUID

    @field_validator("content")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Digite uma mensagem.")
        return value.strip()

@router.get("/config")
def config(request: Request):
    s = request.app.state.settings
    return {"version": "0.1.0", "provider": "Gemini", "models": s.models,
            "configured": bool(s.api_key and s.models), "max_message_chars": 8000,
            "context_turns": 10, "context_chars": 40000,
            "cost_notice": "A API pode ter cotas e custos. O aplicativo não consulta saldo nem garante uso gratuito. Confira seu projeto no Google AI Studio."}

@router.get("/conversations")
def list_conversations(request: Request, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100)):
    with connect(request.app.state.settings.database) as db:
        return [dict(r) for r in db.execute("SELECT * FROM conversations ORDER BY updated_at DESC, id LIMIT ? OFFSET ?", (limit, offset))]

@router.post("/conversations", status_code=201)
def create_conversation(request: Request):
    cid, timestamp = str(uuid4()), now()
    with connect(request.app.state.settings.database) as db:
        db.execute("INSERT INTO conversations VALUES (?, ?, ?, ?)", (cid, "Nova conversa", timestamp, timestamp))
        return require_conversation(db, cid)

@router.get("/conversations/{cid}")
def get_conversation(cid: UUID, request: Request, before: int | None = Query(None, ge=1)):
    with connect(request.app.state.settings.database) as db:
        conversation = require_conversation(db, cid)
        turns = db.execute("SELECT * FROM turns WHERE conversation_id=? AND id<? ORDER BY id DESC LIMIT 51", (str(cid), before if before is not None else 9223372036854775807)).fetchall()
        page = turns[:50]
        return {**conversation, "messages": messages_from_turns(reversed(page)), "next_before": page[-1]["id"] if len(turns) > 50 else None}

@router.delete("/conversations/{cid}", status_code=204)
async def delete_conversation(cid: UUID, request: Request, confirm: bool = False):
    if not confirm:
        raise HTTPException(400, "Confirme explicitamente a exclusão.")
    if request.app.state.send_lock.locked():
        raise HTTPException(409, "Aguarde a resposta em andamento antes de excluir.")
    async with request.app.state.send_lock:
        with connect(request.app.state.settings.database) as db:
            require_conversation(db, cid)
            db.execute("DELETE FROM conversations WHERE id=?", (str(cid),))

@router.post("/conversations/{cid}/messages")
async def send_message(cid: UUID, payload: SendMessage, request: Request):
    state = request.app.state
    if payload.model not in state.settings.models:
        raise HTTPException(400, "Selecione um modelo autorizado em GEMINI_MODELS no servidor.")
    if state.send_lock.locked():
        raise HTTPException(409, "Há uma resposta em andamento. Aguarde e tente novamente.")
    async with state.send_lock:
        with connect(state.settings.database) as db:
            require_conversation(db, cid)
            existing = db.execute("SELECT * FROM turns WHERE conversation_id=? AND request_id=?", (str(cid), str(payload.request_id))).fetchone()
            if existing:
                if existing["user_text"] != payload.content or existing["model"] != payload.model:
                    raise HTTPException(409, "Identificador de envio já usado para outra mensagem.")
                return {"messages": messages_from_turns([existing])}
            turns = list(reversed(db.execute("SELECT * FROM turns WHERE conversation_id=? ORDER BY id DESC LIMIT 10", (str(cid),)).fetchall()))
        # Keep full pairs and bound cost; old history remains in SQLite.
        while turns and sum(len(t["user_text"]) + len(t["assistant_text"]) for t in turns) + len(payload.content) > 40000:
            turns.pop(0)
        context = messages_from_turns(turns) + [{"role": "user", "content": payload.content}]
        try:
            answer = await state.provider.generate(payload.model, context)
        except ProviderError as exc:
            raise HTTPException(exc.status, exc.message) from None
        timestamp = now()
        with connect(state.settings.database) as db:
            db.execute("INSERT INTO turns(conversation_id, request_id, user_text, assistant_text, model, created_at) VALUES (?, ?, ?, ?, ?, ?)", (str(cid), str(payload.request_id), payload.content, answer, payload.model, timestamp))
            db.execute("UPDATE conversations SET title=CASE WHEN title='Nova conversa' THEN ? ELSE title END, updated_at=? WHERE id=?", (payload.content[:60], timestamp, str(cid)))
            turn = db.execute("SELECT * FROM turns WHERE conversation_id=? AND request_id=?", (str(cid), str(payload.request_id))).fetchone()
            return {"messages": messages_from_turns([turn])}
