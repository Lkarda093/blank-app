import asyncio
import httpx
import pytest
from app.providers.gemini import GeminiProvider
from app.providers.base import ProviderError

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
