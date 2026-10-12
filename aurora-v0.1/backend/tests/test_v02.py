import copy
import json
import sqlite3
import time
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.database import connect, initialize
from app.main import create_app
from app.auth.dependencies import COOKIE
from app.data import routes as data_routes

TOKEN = 'test-owner-token-with-more-than-32-characters'
HEADERS = {'Authorization':'Bearer '+TOKEN}
BROWSER = {'X-Aurora-Request':'1'}

class CaptureProvider:
    def __init__(self): self.personalization = None
    async def generate(self, model, messages, personalization=''):
        self.personalization = personalization
        return 'Resposta de teste sobre árvores e arquitetura.'

@pytest.fixture
def setup(tmp_path):
    settings = Settings(TOKEN, 'fake-api-key', ('test-model',), tmp_path/'aurora.sqlite3')
    provider = CaptureProvider()
    with TestClient(create_app(settings, provider)) as client:
        client.headers.update(HEADERS)
        yield client, settings, provider

def create(c):
    r=c.post('/api/conversations'); assert r.status_code==201
    return r.json()['id']
def send(c,cid,text='Olá'):
    return c.post(f'/api/conversations/{cid}/messages',json={'content':text,'model':'test-model','request_id':str(uuid4())})
def preview(c, backup):
    r=c.post('/api/data/restore/preview',json=backup);assert r.status_code==200,r.text
    return r.json()
def restore(c,backup,info=None,**headers):
    info=info or preview(c,backup)
    return c.post('/api/data/restore',json=backup,headers={
        'X-Aurora-Confirm':'RESTAURAR','X-Aurora-Revision':str(info['expected_revision']),
        'X-Aurora-Preview':info['ticket'],'X-Aurora-Preferences-Consent':'1',**headers})

def test_rename_unicode_search_and_full_export(setup):
    c,_,_=setup; cid=create(c)
    assert send(c,cid,'Planejar intervenção urbana').status_code==200
    assert c.patch(f'/api/conversations/{cid}',json={'title':'  Minha ÁREA  '}).json()['title']=='Minha ÁREA'
    for query in ['ÁREA','área','árvores','INTERVENÇÃO']:
        assert c.get('/api/conversations',params={'q':query}).json()[0]['id']==cid
    for query in ['%', "' OR 1=1--",'missing']:
        assert c.get('/api/conversations',params={'q':query}).json()==[]
    for text in ['', ' '*5, 'x'*121]:
        assert c.patch(f'/api/conversations/{cid}',json={'title':text}).status_code==422
    for i in range(51): send(c,cid,str(i))
    exported=c.get(f'/api/conversations/{cid}/export?format=json')
    assert len(exported.json()['messages'])==104
    assert 'attachment' in exported.headers['content-disposition']
    text=c.get(f'/api/conversations/{cid}/export?format=txt').text
    assert 'Minha ÁREA' in text and 'intervenção' in text and '50' in text
    assert c.get(f'/api/conversations/{cid}/export?format=html').status_code==422

def test_preferences_consent_update_delete_and_provider_context(setup):
    c,_,provider=setup
    assert c.get('/api/preferences').json()=={'saved':None}
    prefs={'name':'Willhas','response_style':'conciso','notes':'Explicar com exemplos.'}
    assert c.put('/api/preferences',json=prefs).status_code==400
    cid=create(c);send(c,cid)
    assert 'Preferências fornecidas' not in provider.personalization
    assert c.put('/api/preferences',json={**prefs,'consent':True}).status_code==200
    send(c,cid)
    assert 'Willhas' in provider.personalization and 'conciso' in provider.personalization
    assert c.put('/api/preferences',json={**prefs,'name':'Novo nome','consent':True}).status_code==200
    assert c.get('/api/preferences').json()['saved']['name']=='Novo nome'
    assert c.delete('/api/preferences').status_code==400
    assert c.delete('/api/preferences?confirm=true').status_code==204
    send(c,cid)
    assert 'Preferências fornecidas' not in provider.personalization
    assert c.put('/api/preferences',json={**prefs,'notes':'x'*1001,'consent':True}).status_code==422

def test_backup_restore_roundtrip_with_recovery_and_session_preserved(setup):
    c,s,_=setup; cid=create(c);send(c,cid,'Dados que serão restaurados')
    c.put('/api/preferences',json={'name':'Ana','consent':True})
    backup=c.get('/api/data/backup').json()
    assert set(backup)=={'format','schema_version','exported_at','conversations','turns','preferences','documents','attachments','document_contexts','profiles','projects','memories','conversation_contexts','project_documents','turn_workspaces'}
    assert TOKEN not in json.dumps(backup) and s.api_key not in json.dumps(backup)
    c.delete(f'/api/conversations/{cid}?confirm=true'); newer=create(c)
    info=preview(c,backup)
    assert info['current']['conversations']==1 and info['turns']==1
    result=restore(c,backup,info);assert result.status_code==200,result.text
    assert c.get(f'/api/conversations/{newer}').status_code==404
    assert c.get(f'/api/conversations/{cid}').json()['messages'][0]['content']=='Dados que serão restaurados'
    assert c.get('/api/preferences').json()['saved']['name']=='Ana'
    recovery=c.get('/api/data/recovery').json();assert len(recovery)==1
    before=c.get('/api/data/recovery/'+recovery[0]['id']).json()
    assert before['conversations'][0]['id']==newer
    assert restore(c,before).status_code==200
    assert c.get(f'/api/conversations/{newer}').status_code==200

def test_restore_requires_confirmation_preview_and_preference_consent(setup):
    c,_,_=setup;create(c); c.put('/api/preferences',json={'name':'Ana','consent':True})
    backup=c.get('/api/data/backup').json();info=preview(c,backup)
    assert c.post('/api/data/restore',json=backup).status_code==400
    assert restore(c,backup,info,**{'X-Aurora-Preview':'wrong'}).status_code==409
    assert restore(c,backup,info,**{'X-Aurora-Preferences-Consent':'0'}).status_code==400
    modified=copy.deepcopy(backup);modified['preferences']['name']='Alterado'
    assert restore(c,modified,info).status_code==409
    assert c.get('/api/preferences').json()['saved']['name']=='Ana'

@pytest.mark.parametrize('mutation',['create','send','rename','preferences','delete'])
def test_restore_rejects_stale_preview(setup,mutation):
    c,_,_=setup;cid=create(c);send(c,cid)
    backup=c.get('/api/data/backup').json(); info=preview(c,backup)
    if mutation=='create': create(c)
    if mutation=='send': send(c,cid,'Nova mensagem')
    if mutation=='rename': c.patch(f'/api/conversations/{cid}',json={'title':'Novo título'})
    if mutation=='preferences': c.put('/api/preferences',json={'name':'Ana','consent':True})
    if mutation=='delete': c.delete(f'/api/conversations/{cid}?confirm=true')
    assert restore(c,backup,info).status_code==409

@pytest.mark.parametrize('corruption',['unknown','version','orphan','duplicate_conversation','duplicate_turn','duplicate_request','missing','date'])
def test_invalid_backup_is_rejected_without_changes(setup,corruption):
    c,_,_=setup;cid=create(c);send(c,cid)
    backup=c.get('/api/data/backup').json()
    broken=copy.deepcopy(backup)
    if corruption=='unknown': broken['secret']='not allowed'
    if corruption=='version': broken['schema_version']=99
    if corruption=='orphan': broken['turns'][0]['conversation_id']=str(uuid4())
    if corruption=='duplicate_conversation': broken['conversations'].append(broken['conversations'][0])
    if corruption=='duplicate_turn': broken['turns'].append(broken['turns'][0])
    if corruption=='duplicate_request': broken['turns'].append({**broken['turns'][0],'id':999})
    if corruption=='missing': del broken['preferences']
    if corruption=='date': broken['turns'][0]['created_at']='yesterday'
    assert c.post('/api/data/restore/preview',json=broken).status_code==422
    assert c.get('/api/data/backup').json()['turns']==backup['turns']

def test_restore_during_generation_is_blocked(setup):
    c,_,_=setup;backup=c.get('/api/data/backup').json();info=preview(c,backup)
    c.portal.call(c.app.state.send_lock.acquire)
    try: assert restore(c,backup,info).status_code==409
    finally: c.portal.call(c.app.state.send_lock.release)

def test_restore_rolls_back_when_database_insert_fails(setup):
    c,s,_=setup;cid=create(c);send(c,cid)
    backup=c.get('/api/data/backup').json(); info=preview(c,backup)
    with connect(s.database) as db:
        db.execute("CREATE TRIGGER reject_restore BEFORE INSERT ON turns BEGIN SELECT RAISE(ABORT,'test failure'); END")
    with pytest.raises(sqlite3.IntegrityError): restore(c,backup,info)
    assert len(c.get(f'/api/conversations/{cid}').json()['messages'])==2
    assert len(c.get('/api/data/recovery').json())==1

def test_size_and_malformed_payload_limits(setup,monkeypatch):
    c,_,_=setup
    assert c.post('/api/data/restore/preview',content=b'not JSON').status_code==422
    monkeypatch.setattr(data_routes,'MAX_BYTES',100)
    assert c.post('/api/data/restore/preview',content=b'x'*101).status_code==413
    assert c.get('/api/data/backup').status_code==413

def test_all_new_data_routes_require_auth(setup):
    c,_,_=setup;cid=create(c);c.headers.pop('Authorization')
    for url in ['/api/preferences','/api/data/backup','/api/data/stats','/api/data/recovery',f'/api/conversations/{cid}/export']:
        assert c.get(url).status_code==401
    assert c.post('/api/data/restore/preview',json={}).status_code==401
    assert c.post('/api/data/restore',json={}).status_code==401
    assert c.patch(f'/api/conversations/{cid}',json={'title':'test'}).status_code==401

def test_cookie_session_restart_logout_and_csrf(setup):
    c,s,p=setup;c.headers.pop('Authorization')
    assert c.post('/api/auth/login',json={'token':TOKEN}).status_code==403
    assert c.post('/api/auth/login',json={'token':TOKEN},headers={**BROWSER,'Origin':'https://evil.example'}).status_code==403
    result=c.post('/api/auth/login',json={'token':TOKEN,'remember':True},headers=BROWSER)
    assert result.status_code==200
    cookie=result.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'SameSite=strict' in cookie and 'Max-Age=604800' in cookie
    value=c.cookies.get(COOKIE)
    assert TOKEN not in cookie
    with connect(s.database) as db:
        digest=db.execute('SELECT digest FROM sessions').fetchone()[0]
        assert digest != value and digest != TOKEN
    assert c.get('/api/config').status_code==200
    assert c.post('/api/conversations').status_code==403
    assert c.post('/api/conversations',headers=BROWSER).status_code==201
    assert c.post('/api/conversations',headers={**BROWSER,'Origin':'http://evil.example'}).status_code==403
    backup=c.get('/api/data/backup').json();c.headers.update(BROWSER)
    assert restore(c,backup).status_code==200
    assert c.get('/api/auth/session').status_code==200
    with TestClient(create_app(s,p)) as restarted:
        restarted.cookies.set(COOKIE,value)
        assert restarted.get('/api/config').status_code==200
    assert c.post('/api/auth/logout',headers=BROWSER).status_code==204
    c.cookies.set(COOKIE,value)
    assert c.get('/api/config').status_code==401

def test_session_expiration_and_owner_rotation(setup):
    c,s,p=setup;c.headers.pop('Authorization')
    c.post('/api/auth/login',json={'token':TOKEN},headers=BROWSER)
    value=c.cookies.get(COOKIE)
    rotated=Settings('new-owner-token-that-is-more-than-32-characters',s.api_key,s.models,s.database)
    with TestClient(create_app(rotated,p)) as other:
        other.cookies.set(COOKIE,value)
        assert other.get('/api/config').status_code==401
    with connect(s.database) as db: db.execute('UPDATE sessions SET expires_at=?',(int(time.time())-1,))
    assert c.get('/api/config').status_code==401

def test_secure_cookie_on_https_and_failed_login_limit(setup):
    c,s,p=setup
    with TestClient(create_app(s,p),base_url='https://example.test') as secure:
        r=secure.post('/api/auth/login',json={'token':TOKEN},headers={**BROWSER,'Origin':'https://example.test'})
        assert r.status_code==200 and 'Secure' in r.headers['set-cookie']
        assert secure.get('/api/config').status_code==200
        for i in range(5):
            assert secure.post('/api/auth/login',json={'token':'wrong'},headers=BROWSER).status_code==401
        assert secure.post('/api/auth/login',json={'token':'wrong'},headers=BROWSER).status_code==429

def test_migrates_real_v01_database_and_preserves_safety_copy(tmp_path):
    path=tmp_path/'existing.sqlite3'
    db=sqlite3.connect(path)
    db.executescript('''CREATE TABLE conversations(id TEXT PRIMARY KEY,title TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
    CREATE TABLE turns(id INTEGER PRIMARY KEY AUTOINCREMENT,conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE, request_id TEXT NOT NULL,user_text TEXT NOT NULL,assistant_text TEXT NOT NULL,model TEXT NOT NULL,created_at TEXT NOT NULL, UNIQUE(conversation_id,request_id));
    PRAGMA user_version=1;''')
    cid=str(uuid4());stamp='2026-10-11T20:00:00+00:00'
    db.execute('INSERT INTO conversations VALUES(?,?,?,?)',(cid,'Histórico antigo',stamp,stamp))
    db.execute('INSERT INTO turns VALUES(1,?,?,?,?,?,?)',(cid,str(uuid4()),'Oi','Olá','test-model',stamp))
    db.commit();db.close()
    initialize(path)
    with connect(path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==4
        assert db.execute('SELECT user_text FROM turns').fetchone()[0]=='Oi'
    copies=list((tmp_path/'backups').glob('before-upgrade-v0.6-*.sqlite3'))
    assert len(copies)==1
    with connect(copies[0]) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==1
        assert db.execute('SELECT COUNT(*) FROM turns').fetchone()[0]==1
    initialize(path)
    assert len(list((tmp_path/'backups').glob('*.sqlite3')))==1

def test_recovery_write_failure_keeps_original_database(setup,monkeypatch):
    import os
    c,s,_=setup;cid=create(c);send(c,cid)
    backup=c.get('/api/data/backup').json();info=preview(c,backup)
    def unavailable(*args,**kwargs): raise OSError('test disk unavailable')
    monkeypatch.setattr(os,'open',unavailable)
    with pytest.raises(OSError): restore(c,backup,info)
    assert len(c.get(f'/api/conversations/{cid}').json()['messages'])==2
