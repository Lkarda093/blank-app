import io
import json
import sqlite3
from uuid import uuid4
import httpx
import pytest
from pypdf import PdfWriter
from pypdf.generic import NameObject,DictionaryObject,DecodedStreamObject
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.database import connect,initialize
from app.documents.extraction import MAX_FILE_BYTES,extract,ExtractionError

TOKEN='test-owner-token-with-more-than-32-characters'
def pdf_bytes(texts=('',),encrypted=False):
    writer=PdfWriter()
    for text in texts:
        page=writer.add_blank_page(width=300,height=300)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
        if text:
            stream=DecodedStreamObject();escaped=text.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
            stream.set_data(f'BT /F1 12 Tf 20 250 Td ({escaped}) Tj ET'.encode())
            page[NameObject('/Contents')]=writer._add_object(stream)
    if encrypted:writer.encrypt('password')
    data=io.BytesIO();writer.write(data);return data.getvalue()

class Provider:
    def __init__(self):self.calls=[];self.answer='As arvores estao na segunda pagina [D1 p. 2].'
    async def generate(self,model,messages,personalization=''):
        self.calls.append((model,messages,personalization));return self.answer

@pytest.fixture
def setup(tmp_path):
    settings=Settings(TOKEN,'fake-key',('test-model',),tmp_path/'db.sqlite3')
    provider=Provider()
    with TestClient(create_app(settings,provider),headers={'Authorization':'Bearer '+TOKEN}) as client:
        yield client,settings,provider

def upload(c,name='pesquisa.pdf',content=None):
    return c.post('/api/documents',params={'name':name},content=content if content is not None else pdf_bytes(('Primeira pagina sobre cidade.','Segunda pagina: arvores e vegetacao.')),headers={'Content-Type':'application/octet-stream'})

def attach(c,did):
    cid=c.post('/api/conversations').json()['id']
    assert c.put(f'/api/conversations/{cid}/documents/{did}').status_code==204
    return cid

def message(dids=None,consent=True,**changes):
    return {'content':'Onde estao as arvores?','model':'test-model','request_id':str(uuid4()),'document_ids':dids or [],'documents_consent':consent,**changes}

def test_pdf_text_pages_preview_download_and_unicode_name(setup):
    c,s,p=setup;raw=pdf_bytes(('Cidade.','Arvores.'));result=upload(c,'levantamento urbano.pdf',raw)
    assert result.status_code==201;doc=result.json();assert doc['page_count']==2 and doc['char_count']>0
    assert not p.calls
    assert c.get(f"/api/documents/{doc['id']}/pages/2").json()['text']=='Arvores.'
    downloaded=c.get(f"/api/documents/{doc['id']}/download")
    assert downloaded.content==raw and downloaded.headers['content-type']=='application/octet-stream'
    assert 'attachment' in downloaded.headers['content-disposition']
    assert c.get('/api/documents',params={'q':'URBANO','kind':'pdf'}).json()['items'][0]['id']==doc['id']
    assert c.get(f"/api/documents/{doc['id']}/pages/3").status_code==404
    with TestClient(create_app(s,p),headers={'Authorization':'Bearer '+TOKEN}) as restarted:
        assert restarted.get(f"/api/documents/{doc['id']}/pages/2").json()['text']=='Arvores.'


def test_txt_utf8_and_binary_rejection(setup):
    c,_,_=setup
    result=upload(c,'anotações.txt','Árvores no centro histórico.'.encode('utf-8'))
    assert result.status_code==201
    assert c.get(f"/api/documents/{result.json()['id']}/pages/1").json()['text']=='Árvores no centro histórico.'
    assert upload(c,'binary.txt',b'\x00\x01data').status_code==422
    assert upload(c,'control.txt',b'\x01data').status_code==422
    assert upload(c,'latin.txt',b'\xffinvalid').status_code==422


@pytest.mark.parametrize('name,raw,status',[('file.exe',b'abc',415),('file.pdf',b'not PDF',422),('empty.txt',b'',422),('large.txt',b'a'*(MAX_FILE_BYTES+1),413),('long.txt',b'a'*24001,422),('x\n.txt',b'data',400)])
def test_upload_validation_is_atomic(setup,name,raw,status):
    c,_,p=setup
    assert upload(c,name,raw).status_code==status
    assert c.get('/api/documents').json()['items']==[] and not p.calls


@pytest.mark.parametrize('raw,expected',[(pdf_bytes(('',)), 'OCR'),(pdf_bytes(('Text',),True),'senha'),(pdf_bytes(tuple('Text' for _ in range(31))),'30 páginas')])
def test_scanned_encrypted_and_too_many_pages_rejected(setup,raw,expected):
    c,_,_=setup;r=upload(c,content=raw)
    assert r.status_code==422 and expected in r.json()['detail']


def test_partial_text_keeps_physical_page_numbers(setup):
    c,_,_=setup;r=upload(c,content=pdf_bytes(('', 'Texto na pagina dois.')))
    assert r.json()['unreadable_pages']==[1]
    assert c.get(f"/api/documents/{r.json()['id']}/pages/1").json()['warning']
    assert c.get(f"/api/documents/{r.json()['id']}/pages/2").json()['text']=='Texto na pagina dois.'


def test_parser_timeout_is_handled(monkeypatch):
    import subprocess
    def timeout(*args,**kwargs):raise subprocess.TimeoutExpired('private command',12)
    monkeypatch.setattr('app.documents.extraction.subprocess.run',timeout)
    with pytest.raises(ExtractionError,match='tempo e memória'):extract(b'%PDF-1.3 data','pdf')


def test_document_count_limit_and_deduplication(setup):
    c,_,_=setup
    one=upload(c,'one.txt',b'one').json()
    duplicate=upload(c,'again.txt',b'one').json()
    assert duplicate['id']==one['id'] and duplicate['deduplicated'] is True
    for i in range(19):assert upload(c,f'{i}.txt',f'text {i}'.encode()).status_code==201
    assert upload(c,'last.txt',b'new document').status_code==413
    assert len(c.get('/api/documents').json()['items'])==20


def test_selected_only_consent_references_idempotency_and_restart(setup):
    c,s,p=setup;doc=upload(c).json();cid=attach(c,doc['id'])
    secret=upload(c,'private.txt',b'UNSELECTED_PRIVATE_TEXT').json();c.put(f"/api/conversations/{cid}/documents/{secret['id']}")
    data=message([doc['id']],False)
    assert c.post(f'/api/conversations/{cid}/messages',json=data).status_code==400 and not p.calls
    data['documents_consent']=True
    response=c.post(f'/api/conversations/{cid}/messages',json=data)
    assert response.status_code==200;answer=response.json()['messages'][-1]
    assert answer['sources'][0]['page']==2 and answer['sources'][0]['available'] is True
    assert len(answer['documents_used'])==1 and not answer['source_warning']
    assert 'Segunda pagina' in p.calls[0][1][-1]['content'] and 'UNSELECTED_PRIVATE_TEXT' not in str(p.calls)
    assert 'dados não confiáveis' in p.calls[0][2]
    assert c.post(f'/api/conversations/{cid}/messages',json=data).json()==response.json() and len(p.calls)==1
    changed={**data,'document_ids':[secret['id']]}
    assert c.post(f'/api/conversations/{cid}/messages',json=changed).status_code==409
    with TestClient(create_app(s,p),headers={'Authorization':'Bearer '+TOKEN}) as restarted:
        assert c.get(f'/api/conversations/{cid}').json()['messages'][-1]['sources'][0]['page']==2
        assert restarted.post(f'/api/conversations/{cid}/messages',json=data).json()==response.json() and len(p.calls)==1
    exported=c.get(f'/api/conversations/{cid}/export').json()
    assert exported['messages'][-1]['sources'][0]['page']==2
    text_export=c.get(f'/api/conversations/{cid}/export?format=txt').text
    assert 'pesquisa.pdf, p. 2' in text_export and 'D1: pesquisa.pdf' in text_export
    c.delete(f"/api/documents/{doc['id']}?confirm=true")
    assert c.get(f'/api/conversations/{cid}').json()['messages'][-1]['sources'][0]['available'] is False
    assert c.post(f'/api/conversations/{cid}/messages',json=data).status_code==200 and len(p.calls)==1


def test_no_document_selection_sends_no_document_text(setup):
    c,_,p=setup;doc=upload(c).json();cid=attach(c,doc['id'])
    assert c.post(f'/api/conversations/{cid}/messages',json=message()).status_code==200
    assert 'DOCUMENTOS SELECIONADOS' not in p.calls[-1][1][-1]['content']


def test_unattached_duplicate_and_over_budget_selection_blocked(setup):
    c,_,p=setup;d1=upload(c,'one.txt',b'a'*15000).json();cid=attach(c,d1['id']);d2=upload(c,'two.txt',b'b'*15000).json()
    route=f'/api/conversations/{cid}/messages'
    assert c.post(route,json=message([d2['id']])).status_code==400
    assert c.post(route,json=message([d1['id'],d1['id']])).status_code==400
    c.put(f"/api/conversations/{cid}/documents/{d2['id']}")
    assert c.post(route,json=message([d1['id'],d2['id']])).status_code==400
    assert not p.calls


def test_invalid_or_missing_references_are_not_presented_as_verified(setup):
    c,_,p=setup;doc=upload(c).json();cid=attach(c,doc['id'])
    p.answer='Afirmacao [D1 p. 99] [D2 p. 1].'
    result=c.post(f'/api/conversations/{cid}/messages',json=message([doc['id']])).json()['messages'][-1]
    assert result['sources']==[] and 'não correspondem' in result['source_warning']
    p.answer='Resposta sem citacoes.'
    result=c.post(f'/api/conversations/{cid}/messages',json=message([doc['id']])).json()['messages'][-1]
    assert 'não indicou' in result['source_warning']


def test_detaching_and_deleting_conversation_keep_library(setup):
    c,s,_=setup;doc=upload(c).json();cid=attach(c,doc['id'])
    assert c.delete(f"/api/conversations/{cid}/documents/{doc['id']}").status_code==204
    assert c.get(f'/api/conversations/{cid}/documents').json()==[]
    c.put(f"/api/conversations/{cid}/documents/{doc['id']}")
    assert c.delete(f'/api/conversations/{cid}?confirm=true').status_code==204
    assert c.get(f"/api/documents/{doc['id']}").status_code==200
    assert c.delete(f"/api/documents/{doc['id']}").status_code==400
    assert c.delete(f"/api/documents/{doc['id']}?confirm=true").status_code==204
    with connect(s.database) as db:assert db.execute('SELECT COUNT(*) FROM conversation_documents').fetchone()[0]==0


def restore(c,backup):
    preview=c.post('/api/data/restore/preview',json=backup)
    assert preview.status_code==200,preview.text
    data=preview.json()
    return c.post('/api/data/restore',json=backup,headers={'X-Aurora-Confirm':'RESTAURAR','X-Aurora-Revision':str(data['expected_revision']),'X-Aurora-Preview':data['ticket'],'X-Aurora-Preferences-Consent':'1'})


def test_backup_restores_original_pages_links_references_and_request_identity(setup):
    c,_,p=setup;doc=upload(c).json();cid=attach(c,doc['id']);data=message([doc['id']])
    first=c.post(f'/api/conversations/{cid}/messages',json=data)
    backup=c.get('/api/data/backup').json();assert backup['schema_version']==4 and len(backup['documents'])==1
    c.delete(f"/api/documents/{doc['id']}?confirm=true")
    assert restore(c,backup).status_code==200
    assert c.get(f"/api/documents/{doc['id']}/pages/2").json()['text']=='Segunda pagina: arvores e vegetacao.'
    assert len(c.get(f'/api/conversations/{cid}/documents').json())==1
    assert c.post(f'/api/conversations/{cid}/messages',json=data).json()==first.json() and len(p.calls)==1


def test_old_schema2_backup_is_accepted_and_clears_current_library(setup):
    c,_,_=setup;doc=upload(c).json();cid=attach(c,doc['id'])
    backup=c.get('/api/data/backup').json();backup['schema_version']=2
    for key in ['documents','attachments','document_contexts','profiles','projects','memories','conversation_contexts','project_documents','turn_workspaces']:del backup[key]
    assert restore(c,backup).status_code==200
    assert c.get('/api/documents').json()['items']==[]
    assert c.get(f'/api/conversations/{cid}').status_code==200


@pytest.mark.parametrize('corruption',['hash','text','attachment','source'])
def test_corrupted_document_backup_is_rejected_without_changes(setup,corruption):
    c,_,_=setup;doc=upload(c).json();cid=attach(c,doc['id']);c.post(f'/api/conversations/{cid}/messages',json=message([doc['id']]))
    backup=c.get('/api/data/backup').json()
    if corruption=='hash':backup['documents'][0]['sha256']='0'*64
    elif corruption=='text':backup['documents'][0]['pages'][0]='Manipulated extraction'
    elif corruption=='attachment':backup['attachments'][0]['document_id']=str(uuid4())
    else:backup['document_contexts'][0]['sources'][0]['page']=30
    assert c.post('/api/data/restore/preview',json=backup).status_code==422
    assert c.get(f"/api/documents/{doc['id']}").status_code==200


def test_document_routes_require_auth_and_refuse_mutation_during_generation(setup):
    c,_,_=setup;doc=upload(c).json();cid=attach(c,doc['id'])
    assert c.get('/api/documents',headers={'Authorization':''}).status_code==401
    assert c.get(f"/api/documents/{doc['id']}/download",headers={'Authorization':''}).status_code==401
    async def lock():await c.app.state.send_lock.acquire()
    c.portal.call(lock)
    try:
        assert upload(c,'later.txt',b'text').status_code==409
        assert c.delete(f"/api/documents/{doc['id']}?confirm=true").status_code==409
        assert c.put(f"/api/conversations/{cid}/documents/{doc['id']}").status_code==409
    finally:c.portal.call(c.app.state.send_lock.release)


def test_schema2_migration_preserves_old_turns_and_creates_one_safety_copy(tmp_path):
    path=tmp_path/'db.sqlite3';initialize(path)
    with connect(path) as db:
        db.execute('PRAGMA user_version=2')
        for table in ['turn_document_context','conversation_documents','documents']:db.execute('DROP TABLE '+table)
        cid=str(uuid4());stamp='2026-10-12T00:00:00+00:00';rid=str(uuid4())
        db.execute('INSERT INTO conversations VALUES(?,?,?,?)',(cid,'Old',stamp,stamp))
        db.execute('INSERT INTO turns VALUES(1,?,?,?,?,?,?)',(cid,rid,'Hello','World','test-model',stamp))
    initialize(path);copies=list((tmp_path/'backups').glob('before-upgrade-v0.6-*.sqlite3'));assert len(copies)==1
    with connect(path) as db:
        assert db.execute('SELECT assistant_text FROM turns').fetchone()[0]=='World'
        assert db.execute('PRAGMA user_version').fetchone()[0]==4
    old=sqlite3.connect(copies[0]);assert old.execute('PRAGMA user_version').fetchone()[0]==2;old.close()
    initialize(path);assert len(list((tmp_path/'backups').glob('before-upgrade-v0.6-*.sqlite3')))==1


def test_library_storage_limit_is_checked_before_extraction(setup,monkeypatch):
    c,_,_=setup
    monkeypatch.setattr('app.documents.routes.MAX_STORAGE_BYTES',10)
    assert upload(c,'one.txt',b'123456').status_code==201
    assert upload(c,'two.txt',b'abcdef').status_code==413
    assert c.get('/api/documents').json()['storage_bytes']==6


def test_document_mutation_invalidates_restore_preview(setup):
    c,_,_=setup;upload(c,'one.txt',b'one')
    backup=c.get('/api/data/backup').json();preview=c.post('/api/data/restore/preview',json=backup).json()
    upload(c,'two.txt',b'two')
    result=c.post('/api/data/restore',json=backup,headers={'X-Aurora-Confirm':'RESTAURAR','X-Aurora-Revision':str(preview['expected_revision']),'X-Aurora-Preview':preview['ticket'],'X-Aurora-Preferences-Consent':'1'})
    assert result.status_code==409 and len(c.get('/api/documents').json()['items'])==2


def test_real_gemini_adapter_sends_selected_text_only_and_keeps_it_across_fallback(tmp_path):
    import asyncio
    from app.providers.gemini import GeminiProvider
    bodies=[]
    def handler(request):
        body=json.loads(request.content);bodies.append(body)
        assert request.headers['x-goog-api-key']=='test-key'
        if '/primary:' in str(request.url):return httpx.Response(429)
        assert '/alternate:' in str(request.url)
        return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'Arvores [D1 p. 2].'}]},'finishReason':'STOP'}]})
    upstream=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings=Settings(TOKEN,'test-key',('primary','alternate'),tmp_path/'db.sqlite3',('primary','alternate'))
    try:
        with TestClient(create_app(settings,GeminiProvider(upstream,'test-key')),headers={'Authorization':'Bearer '+TOKEN}) as c:
            doc=upload(c).json();cid=attach(c,doc['id'])
            upload(c,'nao-selecionado.txt',b'NEVER_SEND_THIS_TEXT')
            result=c.post(f'/api/conversations/{cid}/messages',json=message([doc['id']],model='primary',allow_fallback=True))
            assert result.status_code==200 and result.json()['fallback_used'] is True
            assert result.json()['messages'][-1]['sources'][0]['page']==2
            assert len(bodies)==2 and bodies[0]==bodies[1]
            encoded=json.dumps(bodies)
            assert 'Segunda pagina' in encoded and 'NEVER_SEND_THIS_TEXT' not in encoded
            assert 'original_base64' not in encoded and '%PDF' not in encoded
            assert 'dados não confiáveis' in bodies[0]['systemInstruction']['parts'][0]['text']
    finally:asyncio.run(upstream.aclose())


def test_partial_pdf_warns_that_visual_pages_are_not_analyzed(setup):
    c,_,provider=setup;doc=upload(c,content=pdf_bytes(('', 'Texto legivel'))).json();cid=attach(c,doc['id'])
    result=c.post(f'/api/conversations/{cid}/messages',json=message([doc['id']])).json()['messages'][-1]
    assert result['documents_used'][0]['unreadable_pages']==[1]
    assert 'pode não cobrir todo o PDF' in result['source_warning']
    assert 'Sem texto extraído' in provider.calls[-1][1][-1]['content']
