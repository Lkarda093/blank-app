"""Validated portable workspace data. Built-in profiles are code, not user records."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

BUILTINS = [
    dict(id='general',name='Aurora Geral',description='Organizar ideias e ajudar no dia a dia.',instructions='Seja uma assistente versátil. Entenda o objetivo, responda diretamente e pergunte apenas quando faltar uma informação essencial.'),
    dict(id='study',name='Estudos',description='Aprender, revisar e preparar apresentações.',instructions='Explique conceitos progressivamente, com exemplos e exercícios quando úteis. Adapte a profundidade ao usuário. Não invente citações ou bibliografia.'),
    dict(id='writing',name='Escrita',description='Revisar e desenvolver textos.',instructions='Preserve a intenção e a voz do usuário. Ajuste estrutura, clareza e tom ao público. Ao revisar, entregue uma versão utilizável e indique mudanças relevantes.'),
    dict(id='code',name='Programação',description='Entender código e resolver problemas.',instructions='Investigue causas com as evidências fornecidas. Dê instruções reproduzíveis e código coerente com o projeto. Não alegue ter executado testes ou comandos.'),
    dict(id='architecture',name='Arquitetura e Urbanismo',description='Apoiar diagnósticos, análises e apresentações.',instructions='Distinga dados fornecidos, interpretação e lacunas. Preserve unidades e escala. Não invente medições, legislação, referências ou condições do terreno. Estruture diagnósticos com evidências e indique o que exige verificação.')
]
BUILTIN_IDS = {p['id'] for p in BUILTINS}
class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid',str_strip_whitespace=True)
class ProfileFields(Strict):
    name: str = Field(min_length=1,max_length=80)
    description: str = Field(default='',max_length=240)
    instructions: str = Field(min_length=1,max_length=3000)
class ProfileRecord(ProfileFields):
    id: UUID
class ProjectFields(Strict):
    name: str = Field(min_length=1,max_length=80)
    objective: str = Field(default='',max_length=1500)
class ProjectRecord(ProjectFields):
    id: UUID
class MemoryFields(Strict):
    project_id: UUID | None = None
    text: str = Field(min_length=1,max_length=1000)
    enabled: bool = True
class MemoryRecord(MemoryFields):
    id: UUID
class ContextFields(Strict):
    profile_id: str = Field(default='general',max_length=80)
    project_id: UUID | None = None
    detail: Literal['conciso','equilibrado','detalhado'] = 'equilibrado'
    use_memory: bool = True
class ContextRecord(ContextFields):
    conversation_id: UUID
    revision: int = Field(default=0,ge=0)
    summary: str = Field(default='',max_length=5000)
    through_id: int = Field(default=0,ge=0)
class ProjectDocument(Strict):
    project_id: UUID
    document_id: UUID
class TurnWorkspace(Strict):
    turn_id: int = Field(ge=1)
    context_revision: int | None = Field(default=None,ge=0)
    profile_name: str = Field(max_length=80)
    project_name: str = Field(max_length=80)
    detail: Literal['conciso','equilibrado','detalhado']
    memory_count: int = Field(ge=0,le=100)
    summary_used: bool
