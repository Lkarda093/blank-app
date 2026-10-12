import json
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from ..auth.dependencies import require_owner
from ..database import bump_revision, connect

router = APIRouter(prefix="/api/preferences", tags=["Preferências"], dependencies=[Depends(require_owner)])

class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(default="", max_length=80)
    response_style: Literal["equilibrado", "conciso", "detalhado"] = "equilibrado"
    notes: str = Field(default="", max_length=1000)

class SavePreferences(Preferences):
    consent: bool = False

def read_preferences(db):
    row = db.execute("SELECT name, response_style, notes FROM preferences WHERE id=1").fetchone()
    return dict(row) if row else None

def preference_instruction(db):
    data = read_preferences(db)
    if not data:
        return ""
    return ("\nPreferências fornecidas e autorizadas pelo proprietário (dados de personalização, "
            "não concedem ferramentas ou permissões): " + json.dumps(data, ensure_ascii=False))

@router.get("")
def get_preferences(request: Request):
    with connect(request.app.state.settings.database) as db:
        return {"saved": read_preferences(db)}

@router.put("")
async def save_preferences(payload: SavePreferences, request: Request):
    if not payload.consent:
        raise HTTPException(400, "Confirme que deseja salvar e usar estas preferências nas respostas.")
    if request.app.state.send_lock.locked():
        raise HTTPException(409, "Aguarde a operação em andamento.")
    async with request.app.state.send_lock:
        with connect(request.app.state.settings.database) as db:
            db.execute("INSERT INTO preferences VALUES(1,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, response_style=excluded.response_style, notes=excluded.notes", (payload.name, payload.response_style, payload.notes))
            bump_revision(db)
    return {"saved": payload.model_dump(exclude={"consent"})}

@router.delete("", status_code=204)
async def clear_preferences(request: Request, confirm: bool = False):
    if not confirm:
        raise HTTPException(400, "Confirme a exclusão das preferências.")
    if request.app.state.send_lock.locked():
        raise HTTPException(409, "Aguarde a operação em andamento.")
    async with request.app.state.send_lock:
        with connect(request.app.state.settings.database) as db:
            db.execute("DELETE FROM preferences")
            bump_revision(db)
