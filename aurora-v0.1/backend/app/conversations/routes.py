from asyncio import timeout as generation_timeout
from datetime import datetime, timezone
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from ..auth.dependencies import require_owner
from ..database import connect, bump_revision
from ..providers.base import ProviderError
from ..memory.routes import preference_instruction
from ..data.routes import download
import json

router = APIRouter(prefix="/api", dependencies=[Depends(require_owner)])

def turn_result(turn, requested_model):
    return {"messages": messages_from_turns([turn]), "model_used": turn["model"],
            "requested_model": requested_model, "fallback_used": turn["model"] != requested_model}

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
    allow_fallback: bool = False

    @field_validator("content")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Digite uma mensagem.")
        return value.strip()

@router.get("/config")
def config(request: Request):
    s = request.app.state.settings
    return {"version": "0.3.2", "provider": "Gemini", "models": s.models,
            "free_fallback_models": s.free_fallback_models, "fallback_max_models": 3,
            "configured": bool(s.api_key and s.models), "max_message_chars": 8000,
            "context_turns": 10, "context_chars": 40000,
            "cost_notice": "A API pode ter cotas e custos. O aplicativo não consulta saldo nem garante uso gratuito. Confira seu projeto no Google AI Studio."}

@router.get("/conversations")
def list_conversations(request: Request, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), q: str = Query("", max_length=200)):
    # Literal substring search: %, _ and SQL text have no wildcard meaning.
    with connect(request.app.state.settings.database) as db:
        return [dict(r) for r in db.execute("""SELECT c.* FROM conversations c
            WHERE instr(casefold(c.title),casefold(?))>0 OR EXISTS (
                SELECT 1 FROM turns t WHERE t.conversation_id=c.id
                AND (instr(casefold(t.user_text),casefold(?))>0 OR instr(casefold(t.assistant_text),casefold(?))>0))
            ORDER BY c.updated_at DESC,c.id LIMIT ? OFFSET ?""", (q, q, q, limit, offset))]

@router.post("/conversations", status_code=201)
async def create_conversation(request: Request):
    if request.app.state.send_lock.locked():
        raise HTTPException(409, "Aguarde a operação em andamento.")
    async with request.app.state.send_lock:
        cid, timestamp = str(uuid4()), now()
        with connect(request.app.state.settings.database) as db:
            db.execute("INSERT INTO conversations VALUES (?, ?, ?, ?)", (cid, "Nova conversa", timestamp, timestamp))
            bump_revision(db)
            return require_conversation(db, cid)

class Rename(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    @field_validator("title")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Informe um título.")
        return value.strip()

@router.patch("/conversations/{cid}")
async def rename(cid: UUID, payload: Rename, request: Request):
    if request.app.state.send_lock.locked():
        raise HTTPException(409, "Aguarde a operação em andamento.")
    async with request.app.state.send_lock:
        with connect(request.app.state.settings.database) as db:
            require_conversation(db, cid)
            db.execute("UPDATE conversations SET title=?, updated_at=? WHERE id=?", (payload.title, now(), str(cid)))
            bump_revision(db)
            return require_conversation(db, cid)

@router.get("/conversations/{cid}/export")
def export(cid: UUID, request: Request, format: str = Query("json", pattern="^(json|txt)$")):
    with connect(request.app.state.settings.database) as db:
        db.execute("BEGIN")
        conversation = require_conversation(db, cid)
        turns = db.execute("SELECT * FROM turns WHERE conversation_id=? ORDER BY id", (str(cid),)).fetchall()
        messages = messages_from_turns(turns)
    if format == "txt":
        text = conversation["title"] + "\n\n" + "\n\n".join(f'{"Você" if m["role"] == "user" else "Aurora"} ({m["created_at"]}):\n{m["content"]}' for m in messages)
        return download(text, f"aurora-conversa-{cid}.txt", "text/plain")
    return download(json.dumps({"format": "aurora-conversation", "version": 1, "conversation": conversation, "messages": messages}, ensure_ascii=False, indent=2), f"aurora-conversa-{cid}.json")

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
            bump_revision(db)

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
                origin = db.execute("SELECT requested_model FROM request_origins WHERE turn_id=?", (existing["id"],)).fetchone()
                requested_model = origin["requested_model"] if origin else existing["model"]
                if existing["user_text"] != payload.content or requested_model != payload.model:
                    raise HTTPException(409, "Identificador de envio já usado para outra mensagem.")
                return turn_result(existing, requested_model)
            personalization = preference_instruction(db)
            turns = list(reversed(db.execute("SELECT * FROM turns WHERE conversation_id=? ORDER BY id DESC LIMIT 10", (str(cid),)).fetchall()))
        # Keep full pairs and bound cost; old history remains in SQLite.
        while turns and sum(len(t["user_text"]) + len(t["assistant_text"]) for t in turns) + len(payload.content) > 40000:
            turns.pop(0)
        context = messages_from_turns(turns) + [{"role": "user", "content": payload.content}]
        models = [payload.model]
        approved = state.settings.free_fallback_models
        if payload.allow_fallback and payload.model in approved:
            models += [m for m in approved if m != payload.model][:2]
        used_model = payload.model
        tried = []
        try:
            # One total budget, one stored turn, and no unapproved model discovery.
            async with generation_timeout(70):
                for used_model in models:
                    tried.append(used_model)
                    try:
                        answer = await state.provider.generate(used_model, context, personalization=personalization)
                        break
                    except ProviderError as exc:
                        if exc.status != 429:
                            raise
                        if used_model == models[-1]:
                            detail = exc.message
                            if len(tried) > 1:
                                detail = "Cota ou limite atingido nos modelos autorizados tentados: " + ", ".join(tried) + ". Aguarde a renovação dos limites."
                            raise ProviderError(429, detail) from None
        except TimeoutError:
            raise HTTPException(504, "A troca de modelos demorou demais. Confira o histórico antes de reenviar; chamadas podem ter consumido cota.") from None
        except ProviderError as exc:
            raise HTTPException(exc.status, exc.message) from None
        timestamp = now()
        with connect(state.settings.database) as db:
            db.execute("INSERT INTO turns(conversation_id, request_id, user_text, assistant_text, model, created_at) VALUES (?, ?, ?, ?, ?, ?)", (str(cid), str(payload.request_id), payload.content, answer, used_model, timestamp))
            db.execute("UPDATE conversations SET title=CASE WHEN title='Nova conversa' AND (SELECT COUNT(*) FROM turns WHERE conversation_id=?)=1 THEN ? ELSE title END, updated_at=? WHERE id=?", (str(cid), payload.content[:60], timestamp, str(cid)))
            bump_revision(db)
            turn = db.execute("SELECT * FROM turns WHERE conversation_id=? AND request_id=?", (str(cid), str(payload.request_id))).fetchone()
            db.execute("INSERT INTO request_origins(turn_id, requested_model) VALUES (?, ?)", (turn["id"], payload.model))
            return turn_result(turn, payload.model)
