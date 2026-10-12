"""Portable, validated JSON backups. No uploaded SQL or executable payloads."""
import asyncio
import base64
import time
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
from ..workspace.models import (ProfileRecord, ProjectRecord, MemoryRecord, ContextRecord, ProjectDocument, TurnWorkspace, BUILTIN_IDS)
from ..documents.extraction import extract, ExtractionError, MAX_FILE_BYTES, MAX_STORAGE_BYTES, MAX_DOCUMENTS, MAX_PAGES, MAX_CHARS

router = APIRouter(prefix="/api/data", tags=["Dados e backups"], dependencies=[Depends(require_owner)])
MAX_BYTES = 32 * 1024 * 1024

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
    requested_model: str | None = Field(default=None, max_length=100, pattern=r"^[a-zA-Z0-9._-]+$")

class DocumentRecord(Record):
    id: UUID
    name: str = Field(min_length=1,max_length=120)
    kind: Literal['pdf','txt']
    size_bytes: int = Field(ge=1,le=MAX_FILE_BYTES)
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    original_base64: str = Field(min_length=1,max_length=4*MAX_FILE_BYTES//3+4)
    pages: list[str] = Field(min_length=1,max_length=MAX_PAGES)
    created_at: str = Field(max_length=50)

    def original(self):
        return base64.b64decode(self.original_base64,validate=True)

    @model_validator(mode='after')
    def document_valid(self):
        raw=self.original()
        if len(raw)!=self.size_bytes or hashlib.sha256(raw).hexdigest()!=self.sha256:
            raise ValueError('Conteúdo do documento não corresponde ao hash e tamanho')
        if '/' in self.name or '\\' in self.name or any(ord(c)<32 or ord(c)==127 for c in self.name) or not self.name.lower().endswith('.'+self.kind):
            raise ValueError('Nome inválido')
        if sum(map(len,self.pages))>MAX_CHARS or not any(text.strip() for text in self.pages):
            raise ValueError('Texto fora dos limites')
        if self.kind=='txt' and len(self.pages)!=1:
            raise ValueError('TXT deve ter uma seção')
        return self

class Attachment(Record):
    conversation_id: UUID
    document_id: UUID

class DocumentUse(Record):
    id: UUID
    name: str = Field(min_length=1,max_length=120)
    label: str = Field(pattern=r'^D[1-3]$')
    page_count: int = Field(ge=1,le=MAX_PAGES)
    unreadable_pages: list[int] = Field(default_factory=list,max_length=MAX_PAGES)

    @model_validator(mode='after')
    def valid_unreadable(self):
        if any(page<1 or page>self.page_count for page in self.unreadable_pages):
            raise ValueError('Página sem texto inválida')
        return self

class SourceRecord(Record):
    document_id: UUID
    name: str = Field(min_length=1,max_length=120)
    label: str = Field(pattern=r'^D[1-3]$')
    page: int = Field(ge=1,le=MAX_PAGES)

class DocumentRequest(Record):
    ids: list[UUID] = Field(max_length=3)
    consent: bool

class TurnContext(Record):
    turn_id: int = Field(ge=1)
    request: DocumentRequest
    documents: list[DocumentUse] = Field(max_length=3)
    sources: list[SourceRecord] = Field(max_length=90)
    warning: str = Field(max_length=300)

class Backup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["aurora-backup"]
    schema_version: Literal[2,3,4]
    exported_at: str = Field(max_length=50)
    conversations: list[ConversationRecord] = Field(max_length=10000)
    turns: list[TurnRecord] = Field(max_length=100000)
    preferences: Preferences | None
    documents: list[DocumentRecord] = Field(default_factory=list,max_length=MAX_DOCUMENTS)
    attachments: list[Attachment] = Field(default_factory=list,max_length=200000)
    document_contexts: list[TurnContext] = Field(default_factory=list,max_length=100000)

    profiles: list[ProfileRecord] = Field(default_factory=list,max_length=30)
    projects: list[ProjectRecord] = Field(default_factory=list,max_length=50)
    memories: list[MemoryRecord] = Field(default_factory=list,max_length=100)
    conversation_contexts: list[ContextRecord] = Field(default_factory=list,max_length=10000)
    project_documents: list[ProjectDocument] = Field(default_factory=list,max_length=1000)
    turn_workspaces: list[TurnWorkspace] = Field(default_factory=list,max_length=100000)

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
        doc_ids={d.id for d in self.documents}
        if len(doc_ids)!=len(self.documents) or len({d.sha256 for d in self.documents})!=len(self.documents) or sum(d.size_bytes for d in self.documents)>MAX_STORAGE_BYTES:
            raise ValueError('Biblioteca duplicada ou acima dos limites')
        if self.schema_version==2 and (self.documents or self.attachments or self.document_contexts):
            raise ValueError('Schema 2 não contém documentos')
        links=set()
        for link in self.attachments:
            pair=(link.conversation_id,link.document_id)
            if link.conversation_id not in ids or link.document_id not in doc_ids or pair in links:
                raise ValueError('Anexo duplicado ou órfão')
            links.add(pair)
        context_ids=set()
        for context in self.document_contexts:
            if context.turn_id not in turn_ids or context.turn_id in context_ids:
                raise ValueError('Contexto órfão ou duplicado')
            context_ids.add(context.turn_id)
            used={d.id:d for d in context.documents}
            if len(used)!=len(context.documents) or context.request.ids!=[d.id for d in context.documents] or not context.request.consent or [d.label for d in context.documents]!=[f'D{i+1}' for i in range(len(context.documents))]:
                raise ValueError('Seleção de documentos inválida')
            for source in context.sources:
                doc=used.get(source.document_id)
                if doc is None or source.label!=doc.label or source.page>doc.page_count or source.name!=doc.name:
                    raise ValueError('Referência de documento inválida')
        if self.schema_version<4 and any((self.profiles,self.projects,self.memories,self.conversation_contexts,self.project_documents,self.turn_workspaces)):
            raise ValueError('Versão antiga não contém workspace')
        profile_ids={str(p.id) for p in self.profiles}
        project_ids={p.id for p in self.projects}
        if len(profile_ids)!=len(self.profiles) or len(project_ids)!=len(self.projects) or len({m.id for m in self.memories})!=len(self.memories):
            raise ValueError('Workspace duplicado')
        if any(m.project_id is not None and m.project_id not in project_ids for m in self.memories):
            raise ValueError('Memória sem projeto')
        seen=set()
        turns_by_id={t.id:t for t in self.turns}
        for context in self.conversation_contexts:
            if context.conversation_id not in ids or context.conversation_id in seen or context.profile_id not in profile_ids|BUILTIN_IDS or (context.project_id is not None and context.project_id not in project_ids):
                raise ValueError('Contexto de conversa inválido')
            seen.add(context.conversation_id)
            if context.through_id and (context.through_id not in turns_by_id or turns_by_id[context.through_id].conversation_id!=context.conversation_id or not context.summary):
                raise ValueError('Resumo aponta para mensagens inválidas')
        seen=set()
        for link in self.project_documents:
            pair=(link.project_id,link.document_id)
            if link.project_id not in project_ids or link.document_id not in doc_ids or pair in seen:
                raise ValueError('Documento de projeto inválido')
            seen.add(pair)
        seen=set()
        for context in self.turn_workspaces:
            if context.turn_id not in turn_ids or context.turn_id in seen:
                raise ValueError('Perfil de resposta inválido')
            seen.add(context.turn_id)
        return self

def snapshot(db):
    documents=[]
    for row in db.execute('SELECT * FROM documents ORDER BY created_at,id'):
        documents.append({'id':row['id'],'name':row['name'],'kind':row['kind'],'size_bytes':row['size_bytes'],'sha256':row['sha256'],
                          'original_base64':base64.b64encode(row['original']).decode('ascii'),'pages':json.loads(row['pages_json']),'created_at':row['created_at']})
    contexts=[]
    for row in db.execute('SELECT * FROM turn_document_context ORDER BY turn_id'):
        contexts.append({'turn_id':row['turn_id'],'request':json.loads(row['request_json']),'documents':json.loads(row['documents_json']),
                         'sources':json.loads(row['sources_json']),'warning':row['warning']})
    return {"format": "aurora-backup", "schema_version": 4,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "conversations": [dict(r) for r in db.execute("SELECT * FROM conversations ORDER BY created_at,id")],
            "turns": [dict(r) for r in db.execute("SELECT t.*,COALESCE(o.requested_model,t.model) AS requested_model FROM turns t LEFT JOIN request_origins o ON o.turn_id=t.id ORDER BY t.id")],
            "preferences": read_preferences(db),'documents':documents,
            'attachments':[dict(row) for row in db.execute('SELECT * FROM conversation_documents ORDER BY conversation_id,document_id')],
            'document_contexts':contexts,
            'profiles':[dict(r) for r in db.execute('SELECT * FROM profiles ORDER BY id')],
            'projects':[dict(r) for r in db.execute('SELECT * FROM projects ORDER BY id')],
            'memories':[dict(r) for r in db.execute('SELECT * FROM memories ORDER BY id')],
            'conversation_contexts':[dict(r) for r in db.execute('SELECT * FROM conversation_context ORDER BY conversation_id')],
            'project_documents':[dict(r) for r in db.execute('SELECT * FROM project_documents ORDER BY project_id,document_id')],
            'turn_workspaces':[dict(turn_id=r['turn_id'],**json.loads(r['context_json'])) for r in db.execute('SELECT * FROM turn_workspace ORDER BY turn_id')]}


def verify_documents(data):
    deadline=time.monotonic()+45
    for doc in data.documents:
        remaining=deadline-time.monotonic()
        if remaining<=0:
            raise ExtractionError('O backup excedeu o tempo de validação de documentos.')
        pages=extract(doc.original(),doc.kind,deadline=min(12,remaining))
        if pages!=doc.pages:
            raise ExtractionError('O texto extraído no backup não corresponde ao documento original.')

def encode_backup(data):
    try:
        data = Backup.model_validate(data).model_dump(mode="json")
        content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    except (ValueError, UnicodeError):
        raise HTTPException(422, "Dados fora dos limites do backup JSON. Preserve o banco SQLite conforme o README.") from None
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "Backup acima de 32 MiB. Use a cópia manual do SQLite descrita no README.")
    return content

async def parse_backup(request):
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BYTES:
            raise HTTPException(413, "O backup deve ter no máximo 32 MiB.")
        chunks.append(chunk)
    try:
        data=Backup.model_validate_json(b"".join(chunks))
        await asyncio.to_thread(verify_documents,data)
        return data
    except (ValueError, UnicodeError):
        raise HTTPException(422, "Arquivo inválido. Selecione um backup JSON completo exportado pela Aurora (schema 2, 3 ou 4).") from None

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
                "preferences_saved": read_preferences(db) is not None, "documents": db.execute("SELECT COUNT(*) FROM documents").fetchone()[0], "projects": db.execute('SELECT COUNT(*) FROM projects').fetchone()[0], "profiles": db.execute('SELECT COUNT(*) FROM profiles').fetchone()[0], "memories": db.execute('SELECT COUNT(*) FROM memories').fetchone()[0], "revision": revision(db)}

@router.post("/restore/preview")
async def preview(request: Request):
    data = await parse_backup(request)
    with connect(request.app.state.settings.database) as db:
        db.execute("BEGIN")
        current = {"conversations": db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0],
                   "turns": db.execute("SELECT COUNT(*) FROM turns").fetchone()[0],
                   "documents": db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]}
        current_revision = revision(db)
    return {"conversations": len(data.conversations), "turns": len(data.turns), "documents": len(data.documents),
            "profiles":len(data.profiles),"projects":len(data.projects),"memories":len(data.memories),
            "workspace_consent_required":bool(data.memories or any(c.summary for c in data.conversation_contexts) or data.profiles or data.projects),
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
    if (data.memories or any(c.summary for c in data.conversation_contexts) or data.profiles or data.projects) and request.headers.get('X-Aurora-Workspace-Consent') != '1':
        raise HTTPException(400,'Autorize restaurar perfis, projetos, memórias e resumos para uso nas respostas.')
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
            db.execute("DELETE FROM documents")
            db.execute('DELETE FROM memories')
            db.execute('DELETE FROM projects')
            db.execute('DELETE FROM profiles')
            for item in data.profiles:
                db.execute('INSERT INTO profiles VALUES(?,?,?,?)',(str(item.id),item.name,item.description,item.instructions))
            for item in data.projects:
                db.execute('INSERT INTO projects VALUES(?,?,?)',(str(item.id),item.name,item.objective))
            for item in data.memories:
                db.execute('INSERT INTO memories VALUES(?,?,?,?)',(str(item.id),str(item.project_id) if item.project_id else None,item.text,item.enabled))
            for c in data.conversations:
                db.execute("INSERT INTO conversations VALUES(?,?,?,?)", (str(c.id), c.title, c.created_at, c.updated_at))
            for t in data.turns:
                db.execute("INSERT INTO turns VALUES(?,?,?,?,?,?,?)", (t.id, str(t.conversation_id), str(t.request_id), t.user_text, t.assistant_text, t.model, t.created_at))
                db.execute('INSERT INTO request_origins VALUES(?,?)',(t.id,t.requested_model or t.model))
            for doc in data.documents:
                db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)',(str(doc.id),doc.name,doc.kind,doc.size_bytes,doc.sha256,doc.original(),json.dumps(doc.pages,ensure_ascii=False),len(doc.pages),sum(map(len,doc.pages)),doc.created_at))
            for link in data.attachments:
                db.execute('INSERT INTO conversation_documents VALUES(?,?)',(str(link.conversation_id),str(link.document_id)))
            for context in data.document_contexts:
                db.execute('INSERT INTO turn_document_context VALUES(?,?,?,?,?)',(context.turn_id,json.dumps(context.request.model_dump(mode="json"),sort_keys=True),json.dumps([d.model_dump(mode='json') for d in context.documents],ensure_ascii=False),json.dumps([r.model_dump(mode='json') for r in context.sources],ensure_ascii=False),context.warning))
            for item in data.conversation_contexts:
                db.execute('INSERT INTO conversation_context VALUES(?,?,?,?,?,?,?,?)',(str(item.conversation_id),item.profile_id,str(item.project_id) if item.project_id else None,item.detail,item.use_memory,item.revision,item.summary,item.through_id))
            db.execute("INSERT OR IGNORE INTO conversation_context SELECT id,'general',NULL,'equilibrado',1,0,'',0 FROM conversations")
            for item in data.project_documents:
                db.execute('INSERT INTO project_documents VALUES(?,?)',(str(item.project_id),str(item.document_id)))
            for item in data.turn_workspaces:
                db.execute('INSERT INTO turn_workspace VALUES(?,?)',(item.turn_id,json.dumps(item.model_dump(exclude={'turn_id'}),ensure_ascii=False)))
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
