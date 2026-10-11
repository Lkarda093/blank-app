import asyncio
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.database import connect
from app.main import create_app
from app.providers.base import ProviderError

TOKEN = 'test-owner-token-that-is-at-least-32-characters'
class FakeProvider:
    def __init__(self): self.calls = []; self.error = None
    async def generate(self, model, messages):
        self.calls.append((model, messages))
        if self.error: raise self.error
        return 'Resposta de teste: ' + messages[-1]['content']

@pytest.fixture
def setup(tmp_path):
    settings = Settings(TOKEN, 'test-api-secret', ('test-model',), tmp_path / 'db.sqlite3')
    provider = FakeProvider()
    with TestClient(create_app(settings, provider)) as client:
        client.headers['Authorization'] = 'Bearer ' + TOKEN
        yield client, provider, settings

def create(client):
    r = client.post('/api/conversations'); assert r.status_code == 201
    return r.json()['id']
def payload(content='Olá'):
    return {'content': content, 'model': 'test-model', 'request_id': str(uuid4())}
def send(client, cid, data=None): return client.post(f'/api/conversations/{cid}/messages', json=data or payload())

def test_auth_health_and_secrets(setup):
    c, _, s = setup
    assert c.get('/api/health', headers={'Authorization': ''}).status_code == 200
    for path in ['/api/config', '/api/conversations']:
        assert c.get(path, headers={'Authorization': ''}).status_code == 401
        assert c.get(path, headers={'Authorization': 'Bearer wrong'}).status_code == 401
    r = c.get('/api/config')
    assert r.json()['configured'] is True
    assert s.api_key not in r.text and TOKEN not in r.text
    assert r.headers['cache-control'] == 'no-store'

def test_conversation_roundtrip_and_restart(setup):
    c, provider, settings = setup
    cid = create(c)
    assert send(c, cid).status_code == 200
    assert c.get('/api/conversations').json()[0]['title'] == 'Olá'
    assert len(c.get(f'/api/conversations/{cid}').json()['messages']) == 2
    assert send(c, cid, payload('Continue')).status_code == 200
    assert [m['role'] for m in provider.calls[-1][1]] == ['user', 'assistant', 'user']
    with TestClient(create_app(settings, FakeProvider()), headers={'Authorization': 'Bearer '+TOKEN}) as restarted:
        assert len(restarted.get(f'/api/conversations/{cid}').json()['messages']) == 4

def test_confirm_and_cascade_delete(setup):
    c, _, settings = setup; cid = create(c); send(c, cid)
    assert c.delete(f'/api/conversations/{cid}').status_code == 400
    assert c.delete(f'/api/conversations/{cid}?confirm=true').status_code == 204
    assert c.get(f'/api/conversations/{cid}').status_code == 404
    with connect(settings.database) as db: assert db.execute('SELECT COUNT(*) FROM turns').fetchone()[0] == 0

def test_idempotency_and_conflict(setup):
    c, p, _ = setup; cid = create(c); data = payload()
    first = send(c, cid, data); second = send(c, cid, data)
    assert first.json() == second.json() and len(p.calls) == 1
    data['content'] = 'Different'
    assert send(c, cid, data).status_code == 409

@pytest.mark.parametrize('content', ['', '   ', 'x'*8001])
def test_invalid_content(setup, content):
    c, p, _ = setup
    assert send(c, create(c), payload(content)).status_code == 422
    assert not p.calls

def test_invalid_model_and_missing_conversation(setup):
    c, p, _ = setup; data = payload(); data['model'] = '../../not-a-model'
    assert send(c, create(c), data).status_code == 400
    assert send(c, str(uuid4())).status_code == 404
    assert not p.calls

def test_failure_atomicity_and_retry(setup):
    c, p, _ = setup; cid = create(c); data = payload()
    p.error = ProviderError(429, 'Cota esgotada')
    assert send(c, cid, data).status_code == 429
    assert c.get(f'/api/conversations/{cid}').json()['messages'] == []
    p.error = None
    assert send(c, cid, data).status_code == 200

def test_context_bounded_and_history_kept(setup):
    c, p, _ = setup; cid = create(c)
    for i in range(13): assert send(c, cid, payload(str(i) + 'x'*3000)).status_code == 200
    context = p.calls[-1][1]
    assert len(context) <= 21 and sum(len(m['content']) for m in context) <= 40000
    assert len(c.get(f'/api/conversations/{cid}').json()['messages']) == 26

def test_pagination(setup):
    c, _, _ = setup; cid = create(c)
    for i in range(52): assert send(c, cid, payload(str(i))).status_code == 200
    page = c.get(f'/api/conversations/{cid}').json()
    assert len(page['messages']) == 100
    older = c.get(f'/api/conversations/{cid}?before={page["next_before"]}').json()
    assert len(older['messages']) == 4 and older['next_before'] is None
    assert not set(m['id'] for m in page['messages']) & set(m['id'] for m in older['messages'])

def test_concurrent_send_and_delete_rejected(setup):
    c, p, _ = setup; cid = create(c)
    async def lock(): await c.app.state.send_lock.acquire()
    c.portal.call(lock)
    try:
        assert send(c, cid).status_code == 409
        assert c.delete(f'/api/conversations/{cid}?confirm=true').status_code == 409
        assert not p.calls
    finally: c.portal.call(c.app.state.send_lock.release)
