import asyncio
import json
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request
from app.config import Settings
from app.main import create_app
from app.providers.gemini import GeminiProvider
from app.providers.base import ProviderError
from app.conversations.routes import stream_message,SendMessage
from app.database import connect

TOKEN='stream-test-owner-token-0000000000000000'
def frame(text='',finish=None,thought=False):
    data={'candidates':[{'content':{'parts':[{'text':text,'thought':thought}]}}]}
    if finish:data['candidates'][0]['finishReason']=finish
    return 'data: '+json.dumps(data)+'\n\n'
class Bytes(httpx.AsyncByteStream):
    def __init__(self,parts):self.parts=parts
    async def __aiter__(self):
        for part in self.parts:yield part.encode()

async def stream_call(handler):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result=[]
        async for text in GeminiProvider(client,'fake-key').stream('test-model',[{'role':'user','content':'Oi'}]):result.append(text)
        return result

def test_adapter_chunked_contract_and_thought_filter():
    def handler(request):
        assert str(request.url).endswith(':streamGenerateContent?alt=sse')
        assert request.headers['x-goog-api-key']=='fake-key' and 'fake-key' not in str(request.url)
        return httpx.Response(200,stream=Bytes([frame('hidden',thought=True),frame('Olá '),frame('mundo','STOP')]))
    assert asyncio.run(stream_call(handler))==['Olá ','mundo']

@pytest.mark.parametrize('kind',['truncated','malformed','blocked','embedded_error'])
def test_stream_failure_never_looks_completed(kind):
    data={'truncated':frame('Parcial'),'malformed':'data: private broken json\n\n','blocked':'data: {"promptFeedback":{"blockReason":"SAFETY"}}\n\n','embedded_error':'data: {"error":{"message":"private upstream"}}\n\n'}[kind]
    with pytest.raises(ProviderError) as error:asyncio.run(stream_call(lambda request:httpx.Response(200,stream=Bytes([data]))))
    assert 'private' not in error.value.message

def test_503_retries_before_stream_only(monkeypatch):
    async def no_wait(seconds):pass
    monkeypatch.setattr('app.providers.streaming.sleep',no_wait)
    calls=[]
    def handler(request):
        calls.append(request.content)
        return httpx.Response(503) if len(calls)<3 else httpx.Response(200,stream=Bytes([frame('Recuperou','STOP')]))
    assert asyncio.run(stream_call(handler))==['Recuperou']
    assert len(calls)==3 and len(set(calls))==1

def test_output_limit_notice():
    chunks=asyncio.run(stream_call(lambda request:httpx.Response(200,stream=Bytes([frame('Parte','MAX_TOKENS')]))))
    assert 'limite de saída' in ''.join(chunks)

class Provider:
    def __init__(self):self.calls=[];self.mode='ok'
    async def stream(self,model,messages,personalization=''):
        self.calls.append((model,messages,personalization))
        if self.mode=='quota' and model=='primary':raise ProviderError(429,'Cota')
        yield 'Primeiro '
        if self.mode=='partial':raise ProviderError(502,'Conexão interrompida')
        yield 'trecho completo.'
    async def generate(self,*args,**kwargs):raise AssertionError('Non-stream path should not run')
@pytest.fixture
def setup(tmp_path):
    p=Provider();s=Settings(TOKEN,'fake',('primary','alternate'),tmp_path/'db.sqlite3',('primary','alternate'))
    app=create_app(s,p)
    with TestClient(app,headers={'Authorization':'Bearer '+TOKEN}) as c:
        cid=c.post('/api/conversations').json()['id'];yield c,p,s,cid,app

def data():return {'content':'Teste','model':'primary','request_id':str(uuid4()),'allow_fallback':True}
def read(c,cid,payload):return [json.loads(line) for line in c.post(f'/api/conversations/{cid}/messages/stream',json=payload).text.splitlines()]

def test_stream_saves_once_after_completion_and_replays(setup):
    c,p,s,cid,_=setup;payload=data();events=read(c,cid,payload)
    assert [e['text'] for e in events if e['type']=='delta']==['Primeiro ','trecho completo.']
    assert events[-1]['type']=='done'
    assert read(c,cid,payload)[-1]==events[-1] and len(p.calls)==1
    assert len(c.get(f'/api/conversations/{cid}').json()['messages'])==2

def test_partial_failure_no_fallback_no_history_and_lock_released(setup):
    c,p,s,cid,app=setup;p.mode='partial';events=read(c,cid,data())
    assert events[-1]['type']=='error' and len(p.calls)==1 and not app.state.send_lock.locked()
    assert c.get(f'/api/conversations/{cid}').json()['messages']==[]
    p.mode='ok';assert read(c,cid,data())[-1]['type']=='done'

def test_stream_fallback_preserves_context_and_records_actual_model(setup):
    c,p,_,cid,_=setup;p.mode='quota';events=read(c,cid,data())
    assert events[-1]['result']['model_used']=='alternate'
    assert [call[0] for call in p.calls]==['primary','alternate'] and p.calls[0][1:]==p.calls[1][1:]

def test_stream_auth_and_validation(setup):
    c,p,_,cid,_=setup
    assert c.post(f'/api/conversations/{cid}/messages/stream',json=data(),headers={'Authorization':''}).status_code==401
    assert c.post(f'/api/conversations/{cid}/messages/stream',json={}).status_code==422
    assert p.calls==[]

def test_disconnect_cancels_generation_and_releases_lock(setup):
    _,p,s,cid,app=setup
    async def run():
        async def blocked(model,messages,personalization=''):
            yield 'Parcial'
            await asyncio.Event().wait()
        p.stream=blocked
        response=await stream_message(cid,SendMessage(**data()),Request({'type':'http','app':app}))
        iterator=response.body_iterator
        while True:
            event=json.loads(await anext(iterator))
            if event['type']=='delta':break
        assert app.state.send_lock.locked()
        await iterator.aclose()
        assert not app.state.send_lock.locked()
    asyncio.run(run())
    with connect(s.database) as db:assert db.execute('SELECT COUNT(*) FROM turns').fetchone()[0]==0

def test_short_stream_uses_smaller_output_budget():
    async def run():
        def handler(request):
            assert json.loads(request.content)['generationConfig']['maxOutputTokens']==1536
            return httpx.Response(200,stream=Bytes([frame('Curta','STOP')]))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result=[]
            async for chunk in GeminiProvider(client,'test').stream('test-model',[{'role':'user','content':'Oi'}],personalization='Detalhe solicitado nesta conversa (prevalece sobre preferências gerais): conciso'):
                result.append(chunk)
            return result
    assert asyncio.run(run())==['Curta']
