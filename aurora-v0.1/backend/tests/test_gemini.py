import asyncio
import httpx
import pytest
from app.providers.gemini import GeminiProvider
from app.providers.base import ProviderError

@pytest.fixture(autouse=True)
def skip_retry_wait(monkeypatch):
    async def no_wait(seconds):
        pass
    monkeypatch.setattr('app.providers.gemini.sleep', no_wait)

async def call(handler, key='secret-test-key'):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return await GeminiProvider(client, key).generate('test-model', [{'role':'user','content':'Oi'}, {'role':'assistant','content':'Olá'}, {'role':'user','content':'Tudo bem?'}])

def test_real_adapter_request_contract():
    import json
    def handler(request):
        assert str(request.url) == 'https://generativelanguage.googleapis.com/v1beta/models/test-model:generateContent'
        assert request.headers['x-goog-api-key'] == 'secret-test-key'
        assert 'secret-test-key' not in str(request.url)
        body = json.loads(request.content)
        assert [m['role'] for m in body['contents']] == ['user','model','user']
        return httpx.Response(200, json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'hidden', 'thought': True},{'text':'Tudo bem.'}]}}]})
    assert asyncio.run(call(handler)) == 'Tudo bem.'

@pytest.mark.parametrize('status,expected', [(400,502),(401,502),(403,502),(404,502),(429,429),(500,502),(503,502)])
def test_upstream_error_redaction(status, expected):
    with pytest.raises(ProviderError) as exc:
        asyncio.run(call(lambda r: httpx.Response(status, text='private secret-test-key upstream body')))
    assert exc.value.status == expected
    assert exc.value.upstream_status == status
    assert 'secret-test-key' not in exc.value.message and 'upstream body' not in exc.value.message

@pytest.mark.parametrize('data,expected', [({},502), ({'promptFeedback':{'blockReason':'SAFETY'}},422), ({'candidates':[{'finishReason':'SAFETY'}]},422), ([],502)])
def test_empty_blocked_and_malformed(data, expected):
    with pytest.raises(ProviderError) as exc: asyncio.run(call(lambda r:httpx.Response(200,json=data)))
    assert exc.value.status == expected

def test_timeout():
    def handler(request): raise httpx.ReadTimeout('secret upstream', request=request)
    with pytest.raises(ProviderError) as exc: asyncio.run(call(handler))
    assert exc.value.status == 504

def test_network_error():
    def handler(request): raise httpx.ConnectError('secret upstream', request=request)
    with pytest.raises(ProviderError) as exc: asyncio.run(call(handler))
    assert exc.value.status == 502

def test_missing_key_does_not_call_network():
    def handler(request): raise AssertionError('Should not call network')
    with pytest.raises(ProviderError) as exc: asyncio.run(call(handler, key=''))
    assert exc.value.status == 503

def test_output_limit_notice():
    result = asyncio.run(call(lambda r:httpx.Response(200,json={'candidates':[{'finishReason':'MAX_TOKENS','content':{'parts':[{'text':'Parte'}]}}]})))
    assert 'limite de saída' in result

def test_saved_preferences_are_sent_as_system_personalization():
    import json
    async def run():
        def handler(request):
            body=json.loads(request.content)
            instruction=body['systemInstruction']['parts'][0]['text']
            assert 'Willhas' in instruction and 'conciso' in instruction
            assert 'Você não possui ferramentas' in instruction
            assert body['contents'][0]['parts'][0]['text']=='Oi'
            return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'Olá!'}]}}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await GeminiProvider(client,'fake-key').generate('test-model',[{'role':'user','content':'Oi'}],personalization='Preferências autorizadas: Willhas, conciso')
    assert asyncio.run(run())=='Olá!'


def test_temporary_errors_recover_with_bounded_backoff(monkeypatch):
    waits, bodies = [], []
    async def capture_wait(seconds):
        waits.append(seconds)
    monkeypatch.setattr('app.providers.gemini.sleep', capture_wait)
    def handler(request):
        bodies.append(request.content)
        if len(bodies) < 3:
            return httpx.Response(500 if len(bodies) == 1 else 503, text='private upstream body')
        return httpx.Response(200, json={'candidates':[{'content':{'parts':[{'text':'Recuperou.'}]}}]})
    assert asyncio.run(call(handler)) == 'Recuperou.'
    assert waits == [0.75, 1.5]
    assert len(bodies) == 3 and len(set(bodies)) == 1


def test_persistent_unavailability_stops_after_three_attempts():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(503, text='private upstream body')
    with pytest.raises(ProviderError) as exc:
        asyncio.run(call(handler))
    assert len(calls) == 3
    assert 'HTTP 503' in exc.value.message and '3 tentativas' in exc.value.message
    assert 'private' not in exc.value.message


@pytest.mark.parametrize('kind', ['success', 'quota', 'model', 'timeout', 'network'])
def test_no_retry_for_success_or_non_transient_failures(kind):
    calls = []
    def handler(request):
        calls.append(request)
        if kind == 'timeout':
            raise httpx.ReadTimeout('private error', request=request)
        if kind == 'network':
            raise httpx.ConnectError('private error', request=request)
        if kind == 'success':
            return httpx.Response(200, json={'candidates':[{'content':{'parts':[{'text':'OK'}]}}]})
        return httpx.Response(429 if kind == 'quota' else 404)
    if kind == 'success':
        assert asyncio.run(call(handler)) == 'OK'
    else:
        with pytest.raises(ProviderError):
            asyncio.run(call(handler))
    assert len(calls) == 1


def test_total_timeout_does_not_expose_upstream_details(monkeypatch):
    calls = []
    def short_deadline(seconds):
        assert seconds == 65
        return asyncio.timeout(0.01)
    monkeypatch.setattr('app.providers.gemini.timeout', short_deadline)
    async def handler(request):
        calls.append(request)
        await asyncio.sleep(0.1)
        return httpx.Response(200, json={'candidates':[{'content':{'parts':[{'text':'Tarde demais'}]}}]})
    with pytest.raises(ProviderError) as exc:
        asyncio.run(call(handler))
    assert exc.value.status == 504 and 'private' not in exc.value.message
    assert len(calls) == 1
