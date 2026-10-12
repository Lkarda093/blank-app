import asyncio
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.database import connect
from app.main import create_app
from app.providers.base import ProviderError

TOKEN='test-owner-token-that-is-at-least-32-characters'
class Provider:
    def __init__(self, failing=None):
        self.calls=[]; self.failing=failing or {}
    async def generate(self, model, messages, personalization=''):
        self.calls.append((model,messages,personalization))
        if model in self.failing:
            raise ProviderError(self.failing[model], 'Erro controlado de teste')
        return 'Resposta por '+model

@pytest.fixture
def setup(tmp_path):
    settings=Settings(TOKEN,'test-key',('primary','alternate','third','fourth'),tmp_path/'db.sqlite3',('primary','alternate','third','fourth'))
    provider=Provider({'primary':429})
    with TestClient(create_app(settings,provider),headers={'Authorization':'Bearer '+TOKEN}) as client:
        cid=client.post('/api/conversations').json()['id']
        yield client,provider,settings,cid

def payload(**kwargs):
    return {'content':'Olá','model':'primary','request_id':str(uuid4()),'allow_fallback':True,**kwargs}

def post(client,cid,data):
    return client.post(f'/api/conversations/{cid}/messages',json=data)

def test_quota_switch_persists_actual_model_and_replays_once(setup):
    client,provider,settings,cid=setup; data=payload()
    first=post(client,cid,data)
    assert first.status_code==200
    assert first.json()['model_used']=='alternate' and first.json()['fallback_used'] is True
    assert first.json()['requested_model']=='primary'
    assert [c[0] for c in provider.calls]==['primary','alternate']
    assert provider.calls[0][1:]==provider.calls[1][1:]
    assert post(client,cid,data).json()==first.json() and len(provider.calls)==2
    with TestClient(create_app(settings,provider),headers={'Authorization':'Bearer '+TOKEN}) as restarted:
        assert post(restarted,cid,data).json()==first.json() and len(provider.calls)==2
        assert restarted.get(f'/api/conversations/{cid}').json()['messages'][-1]['model']=='alternate'
    with connect(settings.database) as db:
        assert db.execute('SELECT COUNT(*) FROM turns').fetchone()[0]==1
    changed={**data,'model':'third'}
    assert post(client,cid,changed).status_code==409


def test_direct_success_never_calls_alternatives(setup):
    client,provider,_,cid=setup; provider.failing={}
    result=post(client,cid,payload())
    assert result.json()['fallback_used'] is False
    assert [c[0] for c in provider.calls]==['primary']


def test_toggle_off_and_default_request_do_not_switch(setup):
    client,provider,_,cid=setup
    assert post(client,cid,payload(allow_fallback=False)).status_code==429
    data=payload();del data['allow_fallback']
    assert post(client,cid,data).status_code==429
    assert [c[0] for c in provider.calls]==['primary','primary']


@pytest.mark.parametrize('status',[403,404,422,502,504])
def test_other_errors_never_switch(setup,status):
    client,provider,_,cid=setup;provider.failing={'primary':status}
    assert post(client,cid,payload()).status_code==status
    assert len(provider.calls)==1


def test_exhaustion_is_bounded_and_saves_no_partial_turn(setup):
    client,provider,_,cid=setup;provider.failing={m:429 for m in ('primary','alternate','third','fourth')}
    result=post(client,cid,payload())
    assert result.status_code==429
    assert [c[0] for c in provider.calls]==['primary','alternate','third']
    assert 'primary, alternate, third' in result.json()['detail']
    assert client.get(f'/api/conversations/{cid}').json()['messages']==[]


def test_server_requires_explicit_approved_list(tmp_path):
    for approved in [(),('alternate',)]:
        settings=Settings(TOKEN,'test-key',('primary','alternate'),tmp_path/(str(len(approved))+'.sqlite3'),approved)
        provider=Provider({'primary':429})
        with TestClient(create_app(settings,provider),headers={'Authorization':'Bearer '+TOKEN}) as client:
            cid=client.post('/api/conversations').json()['id']
            assert post(client,cid,payload()).status_code==429
            assert [c[0] for c in provider.calls]==['primary']


def test_overall_deadline_rolls_back_and_releases_lock(setup,monkeypatch):
    client,provider,_,cid=setup
    def short_deadline(seconds):
        assert seconds==70
        return asyncio.timeout(0.01)
    monkeypatch.setattr('app.conversations.routes.generation_timeout',short_deadline)
    async def slow(*args,**kwargs):
        await asyncio.sleep(0.1)
        return 'Tarde'
    original=provider.generate;provider.generate=slow
    assert post(client,cid,payload()).status_code==504
    assert client.get(f'/api/conversations/{cid}').json()['messages']==[]
    provider.generate=original
    assert post(client,cid,payload()).status_code==200


def test_backup_preserves_used_model_and_delete_cascades(setup):
    client,_,settings,cid=setup
    assert post(client,cid,payload()).status_code==200
    backup=client.get('/api/data/backup').json()
    assert backup['turns'][0]['model']=='alternate'
    assert 'request_origins' not in backup
    assert client.delete(f'/api/conversations/{cid}?confirm=true').status_code==204
    with connect(settings.database) as db:
        assert db.execute('SELECT COUNT(*) FROM request_origins').fetchone()[0]==0


def test_empty_fallback_list_is_exposed_without_secrets(tmp_path):
    settings=Settings(TOKEN,'private-key',('primary',),tmp_path/'db.sqlite3')
    with TestClient(create_app(settings,Provider()),headers={'Authorization':'Bearer '+TOKEN}) as client:
        result=client.get('/api/config')
        assert result.json()['free_fallback_models']==[]
        assert 'private-key' not in result.text


@pytest.mark.parametrize('upstream_status', [500, 503])
def test_temporary_failure_switches_only_after_adapter_exhaustion(setup, upstream_status):
    client, provider, _, cid = setup
    original = provider.generate
    async def generate(model, messages, personalization=''):
        if model == 'primary':
            provider.calls.append((model, messages, personalization))
            raise ProviderError(502, 'Falha temporária após três tentativas', upstream_status=upstream_status)
        return await original(model, messages, personalization)
    provider.generate = generate
    data = payload()
    result = post(client, cid, data)
    assert result.status_code == 200 and result.json()['model_used'] == 'alternate'
    assert [c[0] for c in provider.calls] == ['primary', 'alternate']
    assert provider.calls[0][1:] == provider.calls[1][1:]
    assert post(client, cid, data).json() == result.json() and len(provider.calls) == 2
    assert post(client, cid, payload(allow_fallback=False)).status_code == 502
    assert provider.calls[-1][0] == 'primary' and len(provider.calls) == 3


def test_mixed_quota_and_temporary_exhaustion_reports_last_error(setup):
    client, provider, _, cid = setup
    async def generate(model, messages, personalization=''):
        provider.calls.append((model, messages, personalization))
        if model == 'primary':
            raise ProviderError(429, 'Cota atingida')
        raise ProviderError(502, 'HTTP 503 após três tentativas', upstream_status=503)
    provider.generate = generate
    result = post(client, cid, payload())
    assert result.status_code == 502
    assert 'primary, alternate, third' in result.json()['detail']
    assert 'HTTP 503' in result.json()['detail']
    assert len(provider.calls) == 3
    assert client.get(f'/api/conversations/{cid}').json()['messages'] == []
