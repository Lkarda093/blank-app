import json
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.database import connect, initialize

TOKEN='workspace-test-owner-token-000000000000000'
class Provider:
    def __init__(self): self.calls=[];self.answer='Resposta teste'
    async def generate(self,model,messages,personalization=''):
        self.calls.append((model,messages,personalization));return self.answer
@pytest.fixture
def setup(tmp_path):
    provider=Provider();settings=Settings(TOKEN,'test',('test-model',),tmp_path/'db.sqlite3')
    with TestClient(create_app(settings,provider),headers={'Authorization':'Bearer '+TOKEN}) as c:
        yield c,provider,settings

def create(c):return c.post('/api/conversations').json()['id']
def context(c,cid):return c.get(f'/api/conversations/{cid}/context').json()
def settings(c,cid,**changes):
    old=context(c,cid)
    data={k:old[k] for k in ['profile_id','project_id','detail','use_memory']}
    return c.put(f'/api/conversations/{cid}/context',json={**data,'expected_revision':old['revision'],**changes})
def send(c,cid,**changes):
    return c.post(f'/api/conversations/{cid}/messages',json={'request_id':str(uuid4()),'model':'test-model','content':'Oi','context_revision':context(c,cid)['revision'],**changes})
def project(c,name):return c.post('/api/projects',json={'name':name,'objective':'Objetivo '+name}).json()['id']
def memory(c,text,project_id=None):return c.post('/api/memories',json={'text':text,'project_id':project_id,'consent':True})

def test_profiles_context_restart_audit_and_deletion(setup):
    c,p,s=setup;cid=create(c)
    assert len(c.get('/api/profiles').json())==5
    custom=c.post('/api/profiles',json={'name':'Revisor','instructions':'Revise como poeta','description':'Poesia'}).json()
    assert settings(c,cid,profile_id=custom['id'],detail='conciso').status_code==200
    result=send(c,cid);assert result.status_code==200
    assert 'Revise como poeta' in p.calls[-1][2] and 'conciso' in p.calls[-1][2]
    assert result.json()['messages'][-1]['workspace']['profile_name']=='Revisor'
    with TestClient(create_app(s,p),headers={'Authorization':'Bearer '+TOKEN}) as restarted:
        assert context(restarted,cid)['profile_id']==custom['id']
    assert c.delete('/api/profiles/'+custom['id']).status_code==400
    assert c.delete('/api/profiles/'+custom['id']+'?confirm=true').status_code==204
    assert context(c,cid)['profile_id']=='general'
    assert c.get(f'/api/conversations/{cid}').json()['messages'][-1]['workspace']['profile_name']=='Revisor'

def test_memory_consent_isolation_disable_and_stale_context(setup):
    c,p,_=setup;a=project(c,'Alfa');b=project(c,'Beta');cid=create(c)
    assert c.post('/api/memories',json={'text':'NO_CONSENT'}).status_code==400
    memory(c,'GLOBAL_MEMORY');memory(c,'ALFA_MEMORY',a);memory(c,'BETA_SECRET',b)
    assert settings(c,cid,project_id=a).status_code==200
    assert send(c,cid).status_code==200
    prompt=p.calls[-1][2];assert 'GLOBAL_MEMORY' in prompt and 'ALFA_MEMORY' in prompt and 'BETA_SECRET' not in prompt
    old=context(c,cid)['revision'];memory(c,'NEW_GLOBAL')
    assert send(c,cid,context_revision=old).status_code==409
    assert settings(c,cid,use_memory=False).status_code==200
    send(c,cid);assert 'ALFA_MEMORY' not in p.calls[-1][2] and 'GLOBAL_MEMORY' not in p.calls[-1][2]
    assert c.put(f'/api/conversations/{cid}/context',json={'profile_id':'no-such-profile','expected_revision':context(c,cid)['revision']}).status_code==404

def test_context_replay_after_changes_and_identity_conflict(setup):
    c,p,_=setup;cid=create(c);rid=str(uuid4());rev=context(c,cid)['revision']
    first=send(c,cid,request_id=rid,context_revision=rev)
    settings(c,cid,profile_id='study')
    assert send(c,cid,request_id=rid,context_revision=rev).json()==first.json()
    assert len(p.calls)==1
    assert send(c,cid,request_id=rid).status_code==409

def test_summary_preview_needs_save_preserves_history_and_bounds(setup):
    c,p,_=setup;cid=create(c);send(c,cid,content='DECISAO ANTIGA');send(c,cid,content='PENDENCIA')
    p.answer='Objetivo: estudo. Decisão: usar escala 1:500. Pendente: medidas.'
    result=c.post(f'/api/conversations/{cid}/continuity/preview',json={'model':'test-model'})
    assert result.status_code==200 and result.json()['covered_turns']==2
    assert context(c,cid)['summary']==''
    data=result.json();saved=c.put(f'/api/conversations/{cid}/continuity',json={k:data[k] for k in ('summary','through_id','expected_revision')})
    assert saved.status_code==200
    send(c,cid,content='Continue');assert 'escala 1:500' in p.calls[-1][2] and len(p.calls[-1][1])==1
    assert len(c.get(f'/api/conversations/{cid}').json()['messages'])==6
    assert c.put(f'/api/conversations/{cid}/continuity',json={k:data[k] for k in ('summary','through_id','expected_revision')}).status_code==409
    settings(c,cid,use_memory=False);send(c,cid)
    assert 'escala 1:500' not in p.calls[-1][2] and len(p.calls[-1][1])>1

def test_memory_budget_rejects_before_network(setup):
    c,p,_=setup;cid=create(c)
    for i in range(9):memory(c,str(i)+'x'*999)
    assert send(c,cid).status_code==400 and p.calls==[]

def test_project_documents_search_and_delete_preserve_originals(setup):
    c,p,_=setup;pid=project(c,'Busca');cid=create(c);settings(c,cid,project_id=pid)
    doc=c.post('/api/documents?name=nota.txt',content='Árvore na praça. Escala 1:500.'.encode(),headers={'Content-Type':'application/octet-stream'}).json()
    assert c.put(f"/api/projects/{pid}/documents/{doc['id']}").status_code==204
    hits=c.get('/api/document-search',params={'q':'praça','project_id':pid}).json();assert hits[0]['page']==1 and hits[0]['id']==doc['id']
    other=project(c,'Outro');assert c.get('/api/document-search',params={'q':'praça','project_id':other}).json()==[]
    send(c,cid);assert 'Árvore' not in str(p.calls[-1])
    memory(c,'Apagar junto',pid)
    assert c.delete(f'/api/projects/{pid}?confirm=true').status_code==204
    assert context(c,cid)['project_id'] is None
    assert c.get('/api/memories').json()==[] and c.get(f"/api/documents/{doc['id']}").status_code==200
    assert c.get(f'/api/conversations/{cid}').status_code==200

def restore(c,backup,consent=True):
    preview=c.post('/api/data/restore/preview',json=backup);assert preview.status_code==200,preview.text
    data=preview.json()
    return c.post('/api/data/restore',json=backup,headers={'X-Aurora-Confirm':'RESTAURAR','X-Aurora-Revision':str(data['expected_revision']),'X-Aurora-Preview':data['ticket'],'X-Aurora-Workspace-Consent':'1' if consent else '0','X-Aurora-Preferences-Consent':'1'})

def test_workspace_backup_roundtrip_and_old_import(setup):
    c,p,_=setup;cid=create(c);pid=project(c,'Salvar');memory(c,'LEMBRAR',pid);settings(c,cid,project_id=pid,profile_id='architecture')
    rid=str(uuid4());rev=context(c,cid)['revision'];first=send(c,cid,request_id=rid,context_revision=rev)
    backup=c.get('/api/data/backup').json();assert backup['schema_version']==4
    assert restore(c,backup,False).status_code==400
    c.delete(f'/api/projects/{pid}?confirm=true')
    assert restore(c,backup).status_code==200
    assert context(c,cid)['project_id']==pid and c.get('/api/memories').json()[0]['text']=='LEMBRAR'
    assert send(c,cid,request_id=rid,context_revision=rev).json()==first.json() and len(p.calls)==1
    old={k:v for k,v in backup.items() if k not in ['profiles','projects','memories','conversation_contexts','project_documents','turn_workspaces']};old['schema_version']=3
    assert restore(c,old).status_code==200
    assert c.get('/api/projects').json()==[] and c.get('/api/memories').json()==[]
    assert context(c,cid)['profile_id']=='general'

@pytest.mark.parametrize('kind',['memory','profile','summary','project_doc'])
def test_backup_rejects_orphan_workspace_without_mutating(setup,kind):
    c,p,_=setup;cid=create(c);pid=project(c,'Teste');memory(c,'Preservar',pid)
    backup=c.get('/api/data/backup').json()
    if kind=='memory':backup['memories'][0]['project_id']=str(uuid4())
    if kind=='profile':backup['conversation_contexts'][0]['profile_id']='unknown'
    if kind=='summary':backup['conversation_contexts'][0].update(summary='invalid',through_id=999)
    if kind=='project_doc':backup['project_documents']=[{'project_id':pid,'document_id':str(uuid4())}]
    assert c.post('/api/data/restore/preview',json=backup).status_code==422
    assert c.get('/api/memories').json()[0]['text']=='Preservar'

def test_workspace_auth_required(setup):
    c,_,_=setup
    for path in ['profiles','projects','memories','document-search?q=oi']:
        assert c.get('/api/'+path,headers={'Authorization':''}).status_code==401

def test_schema3_migration_preserves_history_and_copies_once(tmp_path):
    path=tmp_path/'old.sqlite3';initialize(path)
    cid=str(uuid4());stamp='2026-10-12T12:00:00+00:00'
    with connect(path) as db:
        db.execute('INSERT INTO conversations VALUES(?,?,?,?)',(cid,'Preservar',stamp,stamp))
        db.execute('INSERT INTO turns VALUES(1,?,?,?,?,?,?)',(cid,str(uuid4()),'Pergunta antiga','Resposta antiga','test-model',stamp))
        for table in ['turn_workspace','project_documents','conversation_context','memories','profiles','projects']:
            db.execute('DROP TABLE '+table)
        db.execute('PRAGMA user_version=3')
    initialize(path);initialize(path)
    assert len(list((tmp_path/'backups').glob('before-upgrade-v0.6-*.sqlite3')))==1
    with connect(path) as db:
        assert db.execute('SELECT assistant_text FROM turns').fetchone()[0]=='Resposta antiga'
        assert db.execute('SELECT profile_id FROM conversation_context').fetchone()[0]=='general'
        assert db.execute('PRAGMA user_version').fetchone()[0]==4

def test_full_workspace_backup_documents_summary_custom_profile(setup):
    c,p,_=setup;cid=create(c);pid=project(c,'Completo')
    custom=c.post('/api/profiles',json={'name':'Especialista','instructions':'Instrução especial'}).json()
    settings(c,cid,profile_id=custom['id'],project_id=pid)
    doc=c.post('/api/documents?name=decisoes.txt',content=b'Escala 1:500',headers={'Content-Type':'application/octet-stream'}).json()
    c.put(f"/api/projects/{pid}/documents/{doc['id']}")
    send(c,cid);p.answer='Resumo aprovado'
    preview=c.post(f'/api/conversations/{cid}/continuity/preview',json={'model':'test-model'}).json()
    c.put(f'/api/conversations/{cid}/continuity',json={k:preview[k] for k in ('summary','through_id','expected_revision')})
    backup=c.get('/api/data/backup').json()
    c.delete(f'/api/conversations/{cid}?confirm=true');c.delete(f'/api/profiles/{custom["id"]}?confirm=true')
    assert restore(c,backup).status_code==200
    assert context(c,cid)['summary']=='Resumo aprovado' and context(c,cid)['profile_id']==custom['id']
    assert c.get(f'/api/projects/{pid}/documents').json()[0]['id']==doc['id']
    assert len(c.get('/api/conversations',params={'project_id':pid}).json())==1

def test_summary_overlong_output_does_not_mutate(setup):
    c,p,_=setup;cid=create(c);send(c,cid);p.answer='x'*5001
    assert c.post(f'/api/conversations/{cid}/continuity/preview',json={'model':'test-model'}).status_code==422
    assert context(c,cid)['summary']==''
