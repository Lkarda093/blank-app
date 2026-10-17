import asyncio
import importlib.util
import json
from pathlib import Path
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.providers.local import LocalProvider
from app.providers.base import ProviderError

TOKEN = 'desktop-test-owner-token-with-enough-characters'
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('desktop_launcher', ROOT/'desktop'/'launcher.py')
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)


async def collect(kind, content, calls):
    def handler(request):
        calls.append(request)
        if request.url.path == '/api/tags':
            return httpx.Response(200, json={'models':[{'name':'tiny'}]})
        return httpx.Response(200, text=content)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return [part async for part in LocalProvider(client, kind, 'http://127.0.0.1:9999').stream('tiny', [{'role':'user','content':'Oi'}], ' Preferência teste')]


@pytest.mark.parametrize('kind', ['ollama', 'llamacpp'])
def test_local_stream_contract(kind):
    content = ('{"message":{"content":"Olá"},"done":false}\n{"done":true}\n' if kind == 'ollama' else
               'data: {"choices":[{"delta":{"content":"Olá"},"finish_reason":null}]}\n\ndata: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n')
    calls = []
    assert asyncio.run(collect(kind, content, calls)) == ['Olá']
    body = json.loads(calls[-1].content)
    assert body['messages'][0]['role'] == 'system'
    assert 'Preferência teste' in body['messages'][0]['content']
    assert 'authorization' not in calls[-1].headers
    assert all(call.url.host == '127.0.0.1' for call in calls)


@pytest.mark.parametrize('kind,content', [
    ('ollama', '{"message":{"content":"Parcial"}}\n'),
    ('llamacpp', 'data: {"choices":[{"delta":{"content":"Parcial"}}]}\n\ndata: [DONE]\n\n'),
    ('ollama', '{"error":"secret upstream"}\n'),
    ('llamacpp', 'data: broken private payload\n\n')])
def test_local_rejects_incomplete_or_malformed(kind, content):
    with pytest.raises(ProviderError) as exc:
        asyncio.run(collect(kind, content, []))
    assert 'private' not in exc.value.message and 'secret' not in exc.value.message


def test_ollama_cloud_alias_is_rejected_before_chat():
    calls = []
    async def go():
        def handler(request):
            calls.append(request)
            return httpx.Response(200, json={'models':[{'name':'tiny', 'remote_host':'https://cloud.example'}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await LocalProvider(client, 'ollama', 'http://localhost:11434').generate('tiny', [])
    with pytest.raises(ProviderError):
        asyncio.run(go())
    assert len(calls) == 1


@pytest.mark.parametrize('url', ['https://outside.example', 'http://127.0.0.1.evil', 'http://name:pass@localhost:80', 'http://localhost:80/path'])
def test_local_endpoint_must_be_loopback(url):
    with pytest.raises(ValueError):
        Settings(TOKEN, provider='ollama', local_url=url)


def test_local_settings_never_read_cloud_models(tmp_path, monkeypatch):
    from app import config
    monkeypatch.setattr(config, 'ROOT', tmp_path)
    monkeypatch.setenv('AURORA_PROVIDER', 'ollama')
    monkeypatch.setenv('AURORA_LOCAL_MODELS', 'llama3.2:1b')
    monkeypatch.setenv('AURORA_OWNER_TOKEN', TOKEN)
    monkeypatch.setenv('GEMINI_API_KEY', 'never-used')
    monkeypatch.setenv('GEMINI_FREE_FALLBACK_MODELS', 'cloud-model')
    s = Settings.load()
    assert s.models == ('llama3.2:1b',) and not s.api_key and not s.free_fallback_models


def test_desktop_bootstrap_static_auth_csrf_and_single_use(tmp_path):
    dist = tmp_path/'dist'; dist.mkdir(); (dist/'index.html').write_text('Aurora desktop')
    s = Settings(TOKEN, models=('tiny',), database=tmp_path/'data.sqlite3', provider='llamacpp')
    app = desktop.desktop_app(s, dist, 'one-use-ticket', 12345)
    with TestClient(app, base_url='http://127.0.0.1:12345') as client:
        assert client.get('/api/config').status_code == 401
        assert client.get('/desktop/wrong').status_code == 404
        assert client.get('/desktop/one-use-ticket', headers={'sec-fetch-site':'cross-site'}).status_code == 403
        assert client.get('/desktop/one-use-ticket').text == 'Aurora desktop'
        assert client.get('/desktop/one-use-ticket').status_code == 404
        cfg = client.get('/api/config').json()
        assert cfg['configured'] and cfg['local_mode'] and cfg['provider'] == 'llama.cpp local'
        assert client.post('/api/conversations').status_code == 403
        assert client.post('/api/conversations', headers={'X-Aurora-Request':'1','Origin':'https://bad.example'}).status_code == 403
        assert client.post('/api/conversations', headers={'X-Aurora-Request':'1'}).status_code == 201
        assert client.get('/api/config', headers={'host':'bad.example'}).status_code == 400
        assert client.get('/../backend/.env').status_code == 404


def test_local_partial_failure_is_not_saved_and_does_not_fallback(tmp_path):
    class Broken:
        async def stream(self, *args, **kwargs):
            yield 'Parcial'
            raise ProviderError(503, 'Motor desligado')
    s = Settings(TOKEN, models=('tiny',), database=tmp_path/'db.sqlite3', provider='llamacpp')
    with TestClient(create_app(s, Broken()), headers={'Authorization':'Bearer '+TOKEN}) as client:
        cid = client.post('/api/conversations').json()['id']
        events = client.post(f'/api/conversations/{cid}/messages/stream', json={'content':'Oi','model':'tiny','request_id':str(uuid4()),'allow_fallback':True}).text
        assert 'Parcial' in events and '"type": "error"' in events
        assert client.get(f'/api/conversations/{cid}').json()['messages'] == []


def test_engine_args_are_bounded_and_paths_never_interpreted_by_shell(tmp_path):
    binary = tmp_path/'llama-server.exe'; binary.touch()
    model = tmp_path/'model with spaces.gguf'; model.touch()
    cfg = {'provider':'llamacpp', 'binary':str(binary), 'model_file':str(model)}
    desktop.validate_config(cfg)
    args = desktop.engine_command(cfg, 1234)
    assert args[args.index('-m')+1] == str(model)
    assert args[args.index('-ngl')+1] == '0'
    assert args[args.index('--host')+1] == '127.0.0.1'
    assert args[args.index('-c')+1] == '4096'


def test_local_model_name_survives_backup(tmp_path):
    from app.data.routes import Backup
    class Good:
        async def generate(self, *args, **kwargs):
            return 'Resposta local.'
    s = Settings(TOKEN, models=('llama3.2:1b',), database=tmp_path/'db.sqlite3', provider='ollama')
    with TestClient(create_app(s, Good()), headers={'Authorization':'Bearer '+TOKEN}) as client:
        cid = client.post('/api/conversations').json()['id']
        result = client.post(f'/api/conversations/{cid}/messages', json={'content':'Oi','model':'llama3.2:1b','request_id':str(uuid4())})
        assert result.status_code == 200
        response = client.get('/api/data/backup')
        assert response.status_code == 200
        backup = Backup.model_validate(response.json())
        assert backup.turns[0].model == 'llama3.2:1b'


def test_launcher_real_http_lifecycle_with_simulated_window_and_engine(tmp_path, monkeypatch):
    import sys
    import types
    dist = tmp_path/'frontend'/'dist'; dist.mkdir(parents=True)
    (dist/'index.html').write_text('Aurora in a window')
    binary = tmp_path/'engine'; binary.touch()
    model = tmp_path/'tiny.gguf'; model.touch()
    (tmp_path/'desktop.json').write_text(json.dumps({'provider':'llamacpp','binary':str(binary),'model_file':str(model)}))
    monkeypatch.setattr(desktop, 'ROOT', tmp_path)
    monkeypatch.setattr(desktop, 'data_directory', lambda: tmp_path)
    class Process:
        stopped = False
        def poll(self): return 0 if self.stopped else None
        def terminate(self): self.stopped = True
        def wait(self, timeout=None): return 0
    process = Process()
    monkeypatch.setattr(desktop.subprocess, 'Popen', lambda *args, **kwargs: process)
    monkeypatch.setattr(desktop, 'wait_for_engine', lambda *args: None)
    windows = []
    def start(**kwargs):
        with httpx.Client(follow_redirects=True, trust_env=False) as client:
            response = client.get(windows[0])
            assert response.text == 'Aurora in a window'
            origin = str(response.url).rstrip('/')
            assert client.get(origin+'/api/config').json()['local_mode']
    monkeypatch.setitem(sys.modules, 'webview', types.SimpleNamespace(settings={}, create_window=lambda title,url,**kw: windows.append(url), start=start))
    desktop.run()
    assert process.stopped and len(windows) == 1
    with pytest.raises(httpx.RequestError):
        httpx.get(windows[0], timeout=1, trust_env=False)
