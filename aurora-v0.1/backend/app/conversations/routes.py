from asyncio import timeout as generation_timeout
import asyncio
from contextlib import suppress
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from ..auth.dependencies import require_owner
from ..database import connect, bump_revision
from ..providers.base import ProviderError
from ..memory.routes import preference_instruction
from ..data.routes import download
from ..documents.routes import selected_context, answer_sources, DOC_INSTRUCTION
from ..workspace.routes import context_instruction, read_context
import json

router = APIRouter(prefix="/api", dependencies=[Depends(require_owner)])

def turn_result(turn, requested_model, db):
    return {"messages": messages_from_turns([turn], db), "model_used": turn["model"],
            "requested_model": requested_model, "fallback_used": turn["model"] != requested_model}

def now():
    return datetime.now(timezone.utc).isoformat()

def require_conversation(db, cid):
    row = db.execute("SELECT * FROM conversations WHERE id=?", (str(cid),)).fetchone()
    if row is None:
        raise HTTPException(404, "Conversa não encontrada.")
    return dict(row)

def messages_from_turns(turns, db=None):
    messages = []
    for t in turns:
        for role in ("user", "assistant"):
            message={"id": f'{t["id"]}-{role}', "role": role, "content": t[f"{role}_text"], "created_at": t["created_at"], "model": t["model"]}
            if db is not None and role == 'assistant':
                workspace=db.execute('SELECT context_json FROM turn_workspace WHERE turn_id=?',(t['id'],)).fetchone()
                if workspace: message['workspace']=json.loads(workspace['context_json'])
                context=db.execute('SELECT * FROM turn_document_context WHERE turn_id=?',(t['id'],)).fetchone()
                if context:
                    message['documents_used']=json.loads(context['documents_json'])
                    message['sources']=json.loads(context['sources_json'])
                    for source in message['sources']:
                        source['available']=db.execute('SELECT 1 FROM documents WHERE id=?',(source['document_id'],)).fetchone() is not None
                    message['source_warning']=context['warning']
            messages.append(message)
    return messages

class SendMessage(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    model: str = Field(min_length=1, max_length=100)
    request_id: UUID
    allow_fallback: bool = False
    document_ids: list[UUID] = Field(default_factory=list, max_length=3)
    documents_consent: bool = False
    context_revision: int | None = Field(default=None,ge=0)

    @field_validator("content")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Digite uma mensagem.")
        return value.strip()

@router.get("/config")
def config(request: Request):
    s = request.app.state.settings
    with connect(s.database) as db:
        workspace_id=db.execute("SELECT value FROM metadata WHERE key='workspace_id'").fetchone()[0]
    return {"workspace_id":workspace_id,"version": "0.7.0-desktop.1", "provider": "Gemini" if s.provider == "gemini" else ("Ollama local" if s.provider == "ollama" else "llama.cpp local"), "local_mode": s.provider != "gemini", "models": s.models,
            "free_fallback_models": s.free_fallback_models, "fallback_max_models": 3,
            "configured": bool(s.models and (s.provider != "gemini" or s.api_key)), "max_message_chars": 8000,
            "context_turns": 10, "context_chars": 6000 if s.provider != "gemini" else 40000,
            "cost_notice": "Processamento no seu computador. O modo local não troca para serviços na nuvem." if s.provider != "gemini" else "A API pode ter cotas e custos. O aplicativo não consulta saldo nem garante uso gratuito. Confira seu projeto no Google AI Studio."}

@router.get("/conversations")
def list_conversations(request: Request, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), q: str = Query("", max_length=200), project_id: UUID | None = None):
    # Literal substring search: %, _ and SQL text have no wildcard meaning.
    with connect(request.app.state.settings.database) as db:
        return [dict(r) for r in db.execute("""SELECT c.*,w.project_id,w.profile_id FROM conversations c LEFT JOIN conversation_context w ON w.conversation_id=c.id
            WHERE (? IS NULL OR w.project_id=?) AND ( instr(casefold(c.title),casefold(?))>0 OR EXISTS (
                SELECT 1 FROM turns t WHERE t.conversation_id=c.id
                AND (instr(casefold(t.user_text),casefold(?))>0 OR instr(casefold(t.assistant_text),casefold(?))>0)))
            ORDER BY c.updated_at DESC,c.id LIMIT ? OFFSET ?""", (str(project_id) if project_id else None,str(project_id) if project_id else None,q, q, q, limit, offset))]

@router.post("/conversations", status_code=201)
async def create_conversation(request: Request):
    if request.app.state.send_lock.locked():
        raise HTTPException(409, "Aguarde a operação em andamento.")
    async with request.app.state.send_lock:
        cid, timestamp = str(uuid4()), now()
        with connect(request.app.state.settings.database) as db:
            db.execute("INSERT INTO conversations VALUES (?, ?, ?, ?)", (cid, "Nova conversa", timestamp, timestamp))
            db.execute("INSERT OR IGNORE INTO conversation_context VALUES(?,'general',NULL,'equilibrado',1,0,'',0)",(cid,))
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
        messages = messages_from_turns(turns, db)
    if format == "txt":
        blocks=[]
        for m in messages:
            block=f'{"Você" if m["role"] == "user" else "Aurora"} ({m["created_at"]}):\n{m["content"]}'
            if m.get('documents_used'):
                block+='\n\nDocumentos enviados: '+ '; '.join(f'{d["label"]}: {d["name"]}' for d in m['documents_used'])
            if m.get('sources'):
                block+='\nReferências indicadas: '+ '; '.join(f'{r["name"]}, p. {r["page"]}'+(' (excluído)' if not r['available'] else '') for r in m['sources'])
            if m.get('source_warning'):
                block+='\nAviso: '+m['source_warning']
            blocks.append(block)
        text=conversation['title']+'\n\n'+'\n\n'.join(blocks)
        return download(text, f"aurora-conversa-{cid}.txt", "text/plain")
    return download(json.dumps({"format": "aurora-conversation", "version": 1, "conversation": conversation, "messages": messages}, ensure_ascii=False, indent=2), f"aurora-conversa-{cid}.json")

@router.get("/conversations/{cid}")
def get_conversation(cid: UUID, request: Request, before: int | None = Query(None, ge=1)):
    with connect(request.app.state.settings.database) as db:
        conversation = require_conversation(db, cid)
        turns = db.execute("SELECT * FROM turns WHERE conversation_id=? AND id<? ORDER BY id DESC LIMIT 51", (str(cid), before if before is not None else 9223372036854775807)).fetchall()
        page = turns[:50]
        return {**conversation, "messages": messages_from_turns(reversed(page), db), "next_before": page[-1]["id"] if len(turns) > 50 else None}

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

async def generate_message(cid: UUID, payload: SendMessage, request: Request, emit=None):
    state = request.app.state
    if payload.model not in state.settings.models:
        raise HTTPException(400, "Selecione um modelo autorizado na configuração da Aurora.")
    if state.send_lock.locked():
        raise HTTPException(409, "Há uma resposta em andamento. Aguarde e tente novamente.")
    async with state.send_lock:
        with connect(state.settings.database) as db:
            require_conversation(db, cid)
            existing = db.execute("SELECT * FROM turns WHERE conversation_id=? AND request_id=?", (str(cid), str(payload.request_id))).fetchone()
            document_request=json.dumps({'ids':[str(did) for did in payload.document_ids],'consent':bool(payload.document_ids and payload.documents_consent)},sort_keys=True)
            if existing:
                old_workspace=db.execute('SELECT context_json FROM turn_workspace WHERE turn_id=?',(existing['id'],)).fetchone()
                old_revision=json.loads(old_workspace['context_json']).get('context_revision') if old_workspace else None
                if payload.context_revision != old_revision:
                    raise HTTPException(409,'Identificador de envio já usado com outro contexto.')
                old_context=db.execute('SELECT request_json FROM turn_document_context WHERE turn_id=?',(existing['id'],)).fetchone()
                old_request=old_context['request_json'] if old_context else json.dumps({'ids':[],'consent':False},sort_keys=True)
                if old_request != document_request:
                    raise HTTPException(409,"Identificador de envio já usado com outra seleção de documentos.")
                origin = db.execute("SELECT requested_model FROM request_origins WHERE turn_id=?", (existing["id"],)).fetchone()
                requested_model = origin["requested_model"] if origin else existing["model"]
                if existing["user_text"] != payload.content or requested_model != payload.model:
                    raise HTTPException(409, "Identificador de envio já usado para outra mensagem.")
                return turn_result(existing, requested_model, db)
            workspace, workspace_instruction, workspace_audit = context_instruction(db,cid)
            if payload.context_revision is not None and payload.context_revision != workspace['revision']:
                raise HTTPException(409,'O contexto mudou. Reabra a conversa antes de enviar.')
            workspace_audit['context_revision']=payload.context_revision
            document_body, documents_used, allowed_sources = selected_context(db,cid,payload.document_ids,payload.documents_consent)
            personalization = preference_instruction(db) + workspace_instruction + (DOC_INSTRUCTION if documents_used else '')
            turns = list(reversed(db.execute("SELECT * FROM turns WHERE conversation_id=? AND id>? ORDER BY id DESC LIMIT 10", (str(cid), workspace['through_id'] if workspace['use_memory'] and workspace['summary'] else 0)).fetchall()))
        context_limit = 6000 if state.settings.provider != "gemini" else 40000
        # Keep full pairs and bound cost; old history remains in SQLite.
        while turns and sum(len(t["user_text"]) + len(t["assistant_text"]) for t in turns) + len(payload.content) + len(document_body) + len(personalization) > context_limit:
            turns.pop(0)
        if len(payload.content) + len(document_body) + len(personalization) > context_limit:
            raise HTTPException(400,f"O contexto excede {context_limit} caracteres neste modo. Reduza documentos, pergunta ou memórias ativas.")
        context = messages_from_turns(turns) + [{"role": "user", "content": payload.content + document_body}]
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
                        if emit:
                            await emit({'type':'status','model':used_model,'detail':'Tentando outro modelo…' if len(tried)>1 else ('Aguardando o modelo local…' if state.settings.provider != 'gemini' else 'Aguardando o Gemini…')})
                        answer=''
                        if emit and hasattr(state.provider,'stream'):
                            async for chunk in state.provider.stream(used_model,context,personalization=personalization):
                                answer+=chunk
                                await emit({'type':'delta','text':chunk,'model':used_model})
                            answer=answer.strip()
                            if not answer:raise ProviderError(502,'O modelo não retornou texto.')
                        else:
                            answer = await state.provider.generate(used_model, context, personalization=personalization)
                        break
                    except ProviderError as exc:
                        if answer or (exc.status != 429 and exc.upstream_status not in (500, 503)):
                            raise
                        if used_model == models[-1]:
                            detail = exc.message
                            if len(tried) > 1:
                                detail = "Nenhum dos modelos autorizados tentados respondeu: " + ", ".join(tried) + ". Último erro: " + exc.message
                            raise ProviderError(exc.status, detail) from None
        except TimeoutError:
            raise HTTPException(504, "A resposta demorou demais. Confira o histórico e tente uma pergunta menor.") from None
        except ProviderError as exc:
            raise HTTPException(exc.status, exc.message) from None
        sources,source_warning=answer_sources(answer,allowed_sources) if documents_used else ([], '')
        if any(d.get('unreadable_pages') for d in documents_used):
            source_warning=(source_warning+' Páginas sem texto foram omitidas; a resposta pode não cobrir todo o PDF.').strip()
        timestamp = now()
        with connect(state.settings.database) as db:
            db.execute("INSERT INTO turns(conversation_id, request_id, user_text, assistant_text, model, created_at) VALUES (?, ?, ?, ?, ?, ?)", (str(cid), str(payload.request_id), payload.content, answer, used_model, timestamp))
            db.execute("UPDATE conversations SET title=CASE WHEN title='Nova conversa' AND (SELECT COUNT(*) FROM turns WHERE conversation_id=?)=1 THEN ? ELSE title END, updated_at=? WHERE id=?", (str(cid), payload.content[:60], timestamp, str(cid)))
            bump_revision(db)
            turn = db.execute("SELECT * FROM turns WHERE conversation_id=? AND request_id=?", (str(cid), str(payload.request_id))).fetchone()
            db.execute("INSERT INTO request_origins(turn_id, requested_model) VALUES (?, ?)", (turn["id"], payload.model))
            db.execute('INSERT INTO turn_workspace VALUES(?,?)',(turn['id'],json.dumps(workspace_audit,ensure_ascii=False)))
            if documents_used:
                db.execute('INSERT INTO turn_document_context VALUES(?,?,?,?,?)',(turn['id'],document_request,json.dumps(documents_used,ensure_ascii=False),json.dumps(sources,ensure_ascii=False),source_warning))
            return turn_result(turn, payload.model, db)


@router.post('/conversations/{cid}/messages')
async def send_message(cid:UUID,payload:SendMessage,request:Request):
    return await generate_message(cid,payload,request)

@router.post('/conversations/{cid}/messages/stream')
async def stream_message(cid:UUID,payload:SendMessage,request:Request):
    # Auth, CSRF and payload validation occur before opening the response.
    async def events():
        queue=asyncio.Queue(maxsize=64)
        async def produce():
            try:
                result=await generate_message(cid,payload,request,queue.put)
                await queue.put({'type':'done','result':result})
            except HTTPException as exc:
                await queue.put({'type':'error','status':exc.status_code,'detail':exc.detail})
            except Exception:
                await queue.put({'type':'error','status':500,'detail':'Erro interno. Confira o histórico antes de reenviar.'})
        task=asyncio.create_task(produce())
        try:
            yield json.dumps({'type':'status','detail':'Preparando contexto…'})+'\n'
            while True:
                try:
                    event=await asyncio.wait_for(queue.get(),timeout=10)
                except TimeoutError:
                    yield json.dumps({'type':'heartbeat'})+'\n';continue
                yield json.dumps(event,ensure_ascii=False)+'\n'
                if event['type'] in ('done','error'):break
        finally:
            if not task.done():task.cancel()
            with suppress(asyncio.CancelledError):await task
    return StreamingResponse(events(),media_type='application/x-ndjson',headers={'X-Accel-Buffering':'no'})
