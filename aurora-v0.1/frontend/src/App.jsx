import React, { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { api, download, uploadDocument, streamMessage } from './api.js';
import {Icon,Mark} from './UI.jsx';
import Home,{QuickActions} from './Home.jsx';
import History from './History.jsx';
import useDraft,{readDraftStore} from './useDraft.js';
import ResponseContent,{CopyButton} from './ResponseContent.jsx';
import ContextPanel from './ContextPanel.jsx';
const SettingsPanel=lazy(()=>import('./SettingsPanel.jsx'));
const Agents=lazy(()=>import('./Profiles.jsx'));
const WorkspaceManager=lazy(()=>import('./WorkspaceManager.jsx'));
const Library=lazy(()=>import('./DocumentLibrary.jsx'));
const DocumentPreview=lazy(()=>import('./DocumentPreview.jsx'));
const ConversationDocuments=lazy(()=>import('./ConversationDocuments.jsx'));
const Tools=lazy(()=>import('./Modules.jsx').then(m=>({default:m.Tools})));
const Computer=lazy(()=>import('./Modules.jsx').then(m=>({default:m.Computer})));
const Organization=lazy(()=>import('./Modules.jsx').then(m=>({default:m.Organization})));
function stored(key,fallback){try{const value=localStorage.getItem(key);return value===null?fallback:JSON.parse(value);}catch{return fallback;}}
function usePreference(key,fallback){const [value,setValue]=useState(()=>stored(key,fallback));useEffect(()=>{try{localStorage.setItem(key,JSON.stringify(value));}catch{}},[key,value]);return [value,setValue];}
function chooseModel(cfg){const preferred=stored('aurora-model','');return cfg.models.includes(preferred)?preferred:cfg.models[0]||'';}
const navItems=[['chat','Chats','chat'],['agents','Perfis da Aurora','spark'],['plugins','Plugins','plugin'],['library','Biblioteca','folder'],['tools','Ferramentas','tools'],['computer','Computador','computer'],['organization','Projetos e memória','organize'],['settings','Configurações','settings']];
export default function App(){
 const [attachedDocs,setAttachedDocs]=useState([]),[selectedDocs,setSelectedDocs]=useState([]),[documentConsent,setDocumentConsent]=useState(false),[documentNotice,setDocumentNotice]=useState(''),[documentPreview,setDocumentPreview]=useState(null);
 const uploadInput=useRef(null);
 const [theme,setTheme]=useState(()=>{try{const v=localStorage.getItem('aurora-theme');return ['auto','light','dark'].includes(v)?v:'dark';}catch{return 'dark';}});
 const [fallbackEnabled,setFallbackEnabled]=usePreference('aurora-auto-fallback',true);
 const [modelNotice,setModelNotice]=useState('');
 const [partial,setPartial]=useState(''),[partialFailed,setPartialFailed]=useState(false),[sendStage,setSendStage]=useState(''),[pendingQuestion,setPendingQuestion]=useState('');
 const partialBuffer=useRef(''),partialTimer=useRef(null);
 useEffect(()=>()=>clearTimeout(partialTimer.current),[]);
 const [accent,setAccent]=usePreference('aurora-accent','violet');
 const [effects,setEffects]=usePreference('aurora-effects',true);
 const [historySide,setHistorySide]=usePreference('aurora-history-side','left');
 const [pinned,setPinned]=usePreference('aurora-pinned',[]);
 const [systemDark,setSystemDark]=useState(()=>window.matchMedia('(prefers-color-scheme: dark)').matches);
 const resolvedTheme=theme==='auto'?(systemDark?'dark':'light'):theme;
 const token=null;
 const [authenticated,setAuthenticated]=useState(false),[checkingSession,setCheckingSession]=useState(true),[remember,setRemember]=useState(false);
 const [query,setQuery]=useState(''),[searchInput,setSearchInput]=useState(''),[renameValue,setRenameValue]=useState(''),[renaming,setRenaming]=useState(false),[loginToken,setLoginToken]=useState('');
 const [config,setConfig]=useState(null),[conversations,setConversations]=useState([]),[hasMore,setHasMore]=useState(false),[active,setActive]=useState(null),[messages,setMessages]=useState([]),[nextBefore,setNextBefore]=useState(null);
 const [draft,setDraft,selectDraft,forgetDraft,draftWarning]=useDraft(config?.workspace_id);
 const [profiles,setProfiles]=useState([]),[projects,setProjects]=useState([]),[memories,setMemories]=useState([]),[chatContext,setChatContext]=useState(null),[managerTab,setManagerTab]=useState('projects');
 const [model,setModel]=useState(''),[busy,setBusy]=useState(false),[sending,setSending]=useState(false),[error,setError]=useState(''),[view,setView]=useState('chat');
 const [sidebar,setSidebar]=useState(false),[compact,setCompact]=useState(()=>window.matchMedia('(max-width: 900px)').matches),[navCollapsed,setNavCollapsed]=useState(false),[rightOpen,setRightOpen]=useState(true);
 const [deleteTarget,setDeleteTarget]=useState(null),[profile,setProfile]=useState({name:''}),[settingsTab,setSettingsTab]=useState('Geral'),[libraryFilter,setLibraryFilter]=useState('Todos'),[libraryMenu,setLibraryMenu]=useState(false),[agentSearch,setAgentSearch]=useState(''),[planned,setPlanned]=useState('');
 const retry=useRef(null),end=useRef(null),input=useRef(null),gate=useRef(false),historyPanel=useRef(null),historyToggle=useRef(null);
 useEffect(()=>{const media=window.matchMedia('(max-width: 900px)');const update=()=>{setCompact(media.matches);setSidebar(false);};media.addEventListener('change',update);return()=>media.removeEventListener('change',update);},[]);
 useEffect(()=>{const media=window.matchMedia('(prefers-color-scheme: dark)');const update=()=>setSystemDark(media.matches);media.addEventListener('change',update);return()=>media.removeEventListener('change',update);},[]);
 useEffect(()=>{document.documentElement.dataset.theme=resolvedTheme;document.documentElement.dataset.accent=accent;document.documentElement.dataset.effects=effects?'on':'off';try{localStorage.setItem('aurora-theme',theme);}catch{}},[theme,resolvedTheme,accent,effects]);
 useEffect(()=>{if(!sidebar||!compact||deleteTarget||documentPreview)return;const panel=historyPanel.current;panel?.querySelector('button:not(:disabled)')?.focus();const handleKey=event=>{if(event.key==='Escape'){setSidebar(false);return;}if(event.key!=='Tab')return;const elements=[...panel.querySelectorAll('button:not(:disabled), input:not(:disabled), a[href]')].filter(el=>el.getClientRects().length);const first=elements[0],last=elements[elements.length-1];if(!first){event.preventDefault();return;}if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}};document.addEventListener('keydown',handleKey);return()=>{document.removeEventListener('keydown',handleKey);historyToggle.current?.focus();};},[sidebar,compact,deleteTarget,documentPreview]);
 useEffect(()=>{if(renaming)document.getElementById('conversation-title')?.focus();},[renaming]);
 useEffect(()=>{if(messages.length||sending)end.current?.scrollIntoView({behavior:'auto'});},[active,sending]);
 useEffect(()=>{if(deleteTarget)document.getElementById('cancel-delete')?.focus();},[deleteTarget]);
 useEffect(()=>{if(!authenticated)return;let alive=true;api('/preferences').then(data=>{if(alive)setProfile(data.saved||{name:''});}).catch(()=>{});return()=>{alive=false;};},[authenticated]);
 useEffect(()=>{if(model)try{localStorage.setItem('aurora-model',JSON.stringify(model));}catch{}},[model]);
 useEffect(()=>{if(input.current){input.current.style.height='auto';input.current.style.height=Math.min(140,Math.max(45,input.current.scrollHeight))+'px';}},[draft,view]);
 async function reloadWorkspace(){
   const [a,b,c]=await Promise.all([api('/profiles'),api('/projects'),api('/memories')]);setProfiles(a);setProjects(b);setMemories(c);
   if(active)setChatContext(await api(`/conversations/${active.id}/context`));
   await refreshList();
 }
 useEffect(()=>{if(!authenticated||!config?.workspace_id)return;let alive=true;Promise.all([api('/profiles'),api('/projects'),api('/memories')]).then(([a,b,c])=>{if(alive){setProfiles(a);setProjects(b);setMemories(c);}}).catch(e=>{if(alive)setError(e.message);});
 const last=readDraftStore(config.workspace_id).last;if(last)selectConversation(last);
 return()=>{alive=false;};},[authenticated,config?.workspace_id]);
 async function changeContext(changes){
   const conversation=await ensureConversation();
   const current=await api(`/conversations/${conversation.id}/context`);
   const body={profile_id:current.profile_id,project_id:current.project_id,detail:current.detail,use_memory:current.use_memory,...changes,expected_revision:current.revision};
   const updated=await api(`/conversations/${conversation.id}/context`,null,{method:'PUT',body:JSON.stringify(body)});setChatContext(updated);retry.current=null;setModelNotice('Contexto atualizado para as próximas respostas.');await refreshList();
 }
 function navigate(next){setView(next);setSidebar(false);setPlanned('');}
 function prompt(text){setView('chat');setPlanned('');if(text!==null)setDraft(text);setTimeout(()=>input.current?.focus(),0);}
 function openAgents(search=''){setAgentSearch(search);navigate('agents');}
  async function perform(work) {
    if (gate.current) return;
    gate.current = true; setBusy(true); setError('');
    try { await work(); } catch (e) { setError(e.message); if(e.status===401) { setAuthenticated(false); setMessages([]); setConversations([]); setActive(null); } }
    finally { gate.current = false; setBusy(false); }
  }
  async function refreshList(auth = token, search = query) {
    const list = await api(`/conversations?q=${encodeURIComponent(search)}`, auth);
    setConversations(list); setHasMore(list.length === 100);
  }
  async function login(event) {
    event.preventDefault();
    await perform(async () => {
      const auth = loginToken.trim();
      await api('/auth/login', null, { method: 'POST', body: JSON.stringify({token:auth, remember}) });
      setLoginToken('');
      const [cfg, list] = await Promise.all([api('/config'), api('/conversations')]);
      setConfig(cfg); setModel(chooseModel(cfg)); setConversations(list); setHasMore(list.length === 100);
      setAuthenticated(true); setQuery(''); setSearchInput('');
    });
  }
  async function selectConversation(id) {
    await perform(async () => {
      const [data,attachments,context] = await Promise.all([api(`/conversations/${id}`, token),api(`/conversations/${id}/documents`),api(`/conversations/${id}/context`)]);setChatContext(context);selectDraft(id);
      setAttachedDocs(attachments);setSelectedDocs([]);setDocumentConsent(false);setDocumentNotice('');
      setPartial('');setPartialFailed(false);setPendingQuestion('');setActive(data); setMessages(data.messages); setNextBefore(data.next_before);
      setModelNotice(''); retry.current = null; setRenaming(false); setView('chat'); setSidebar(false);
    });
  }
  async function newConversation(projectId=null) {
    if(typeof projectId!=='string')projectId=null;
    await perform(async () => {
      const data = await api('/conversations', token, { method: 'POST' });
      setAttachedDocs([]);setSelectedDocs([]);setDocumentConsent(false);setDocumentNotice('');
      setPartial('');setPartialFailed(false);setPendingQuestion('');setActive(data); setMessages([]); setNextBefore(null); setModelNotice(''); selectDraft(data.id); retry.current = null;
      let ctx=await api(`/conversations/${data.id}/context`);
      if(projectId)ctx=await api(`/conversations/${data.id}/context`,null,{method:'PUT',body:JSON.stringify({profile_id:'general',project_id:projectId,detail:'equilibrado',use_memory:true,expected_revision:ctx.revision})});setChatContext(ctx);
      setQuery(''); setSearchInput(''); await refreshList(null, ''); setRenaming(false); setView('chat'); setSidebar(false);
    });
  }
  async function send(event) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || !config?.configured || !model || (selectedDocs.length && !documentConsent)) return;
    await perform(async () => {
      setSending(true); setModelNotice('');setPartial('');setPartialFailed(false);partialBuffer.current='';setPendingQuestion(text);setSendStage('Preparando contexto…');
      try {
        let conversation = active;
        if (!conversation) {
          conversation = await api('/conversations', token, { method: 'POST' });
          selectDraft(conversation.id,true);setActive(conversation); setConversations(old => [conversation, ...old]);
        }
        const currentContext=chatContext||await api(`/conversations/${conversation.id}/context`);setChatContext(currentContext);
        const context_revision=currentContext.revision;
        const allow_fallback = fallbackEnabled && (config.free_fallback_models || []).includes(model) && (config.free_fallback_models || []).length > 1;
        const document_ids = [...selectedDocs];
        const documents_consent = Boolean(document_ids.length && documentConsent);
        if (!retry.current || retry.current.context_revision!==context_revision || retry.current.content !== text || retry.current.model !== model || retry.current.cid !== conversation.id || retry.current.allow_fallback !== allow_fallback || JSON.stringify(retry.current.document_ids)!==JSON.stringify(document_ids) || retry.current.documents_consent!==documents_consent) {
          retry.current = { content: text, context_revision, model, allow_fallback, document_ids, documents_consent, cid: conversation.id, request_id: crypto.randomUUID() };
        }
        const { cid, ...payload } = retry.current;
        const result = await streamMessage(`/conversations/${cid}/messages/stream`,payload,event=>{
          if(event.type==='status')setSendStage(event.detail);
          if(event.type==='delta'){
            partialBuffer.current+=event.text;setSendStage('Recebendo resposta…');
            if(!partialTimer.current)partialTimer.current=setTimeout(()=>{setPartial(partialBuffer.current);partialTimer.current=null;},60);
          }
        });
        clearTimeout(partialTimer.current);partialTimer.current=null;setPartial('');partialBuffer.current='';setPendingQuestion('');
        setMessages(old => [...old.filter(m => !result.messages.some(n => n.id === m.id)), ...result.messages]);
        if (result.fallback_used) { setModel(result.model_used); setModelNotice(`${result.requested_model} não pôde responder. Aurora respondeu com ${result.model_used}.`); }
        if(document_ids.length){setDocumentConsent(false);setDocumentNotice('Confira os arquivos antes da próxima pergunta.');}
        setDraft(''); retry.current = null;
        setActive(old => ({ ...old, title: old.title === 'Nova conversa' ? text.slice(0, 60) : old.title }));
        await Promise.all([refreshList(),api(`/conversations/${conversation.id}/context`).then(setChatContext)]);
        setTimeout(() => { end.current?.scrollIntoView({ behavior: 'smooth' }); input.current?.focus(); }, 0);
      } catch(e){
        clearTimeout(partialTimer.current);partialTimer.current=null;setPartial(partialBuffer.current);setPartialFailed(Boolean(partialBuffer.current));
        if(e.status===409&&active)setChatContext(await api(`/conversations/${active.id}/context`));
        throw e;
      } finally { setSending(false);setSendStage(''); }
    });
  }
  function clearAccount() {
    setPartial('');setPartialFailed(false);setPendingQuestion('');setAuthenticated(false); setConfig(null); setConversations([]); setMessages([]); setActive(null);
    setAttachedDocs([]);setSelectedDocs([]);setDocumentConsent(false);setDocumentPreview(null);setDocumentNotice('');
    setChatContext(null);setProfiles([]);setProjects([]);setMemories([]);setError(''); setModelNotice(''); setView('chat'); setSidebar(false); setDeleteTarget(null); setProfile({name:''}); retry.current = null;
  }
  async function logout() { await perform(async () => { await api('/auth/logout',null,{method:'POST'}); clearAccount(); }); }
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        await api('/auth/session');
        const [cfg, list] = await Promise.all([api('/config'), api('/conversations')]);
        if(alive) { setConfig(cfg); setModel(chooseModel(cfg)); setConversations(list); setHasMore(list.length===100); setAuthenticated(true); }
      } catch(e) { if(alive && e.status!==401) setError(e.message); }
      finally { if(alive) setCheckingSession(false); }
    })();
    return () => { alive=false; };
  }, []);

 async function ensureConversation(){
   if(active)return active;
   const data=await api('/conversations',null,{method:'POST'});
   selectDraft(data.id,true);setActive(data);setChatContext(await api(`/conversations/${data.id}/context`));setMessages([]);setNextBefore(null);setQuery('');setSearchInput('');await refreshList(null,'');
   return data;
 }
 async function attachDocument(doc){
   const conversation=await ensureConversation();
   await api(`/conversations/${conversation.id}/documents/${doc.id}`,null,{method:'PUT'});
   const list=await api(`/conversations/${conversation.id}/documents`);setAttachedDocs(list);setDocumentConsent(false);
   const ids=selectedDocs.includes(doc.id)?selectedDocs:[...selectedDocs,doc.id];
   if(ids.length<=3&&list.filter(d=>ids.includes(d.id)).reduce((sum,d)=>sum+d.char_count,0)<=24000){setSelectedDocs(ids);setDocumentNotice('Arquivo pronto. Marque a autorização para usar nesta pergunta.');}
   else setDocumentNotice('Documento anexado. O limite de seleção foi atingido; escolha quais documentos usar.');
   setView('chat');setSidebar(false);setPlanned('');retry.current=null;
 }
 function uploadToConversation(file){if(file)perform(async()=>{setDocumentNotice('Lendo arquivo…');try{const doc=await uploadDocument(file);await attachDocument(doc);}catch(e){setDocumentNotice('');throw e;}});}
 function selectDocument(doc){
   const ids=selectedDocs.includes(doc.id)?selectedDocs.filter(id=>id!==doc.id):[...selectedDocs,doc.id];
   const chars=attachedDocs.filter(d=>ids.includes(d.id)).reduce((sum,d)=>sum+d.char_count,0);
   if(ids.length>3||chars>24000){setDocumentNotice('Selecione no máximo 3 arquivos e 24 mil caracteres no total.');return;}
   setSelectedDocs(ids);setDocumentConsent(false);setDocumentNotice('');
 }
 function documentDeleted(id){
   setAttachedDocs(old=>old.filter(d=>d.id!==id));setSelectedDocs(old=>old.filter(d=>d!==id));setDocumentConsent(false);
   setMessages(old=>old.map(m=>({...m,sources:m.sources?.map(s=>s.document_id===id?{...s,available:false}:s)})));
 }
 function detachDocument(id){perform(async()=>{await api(`/conversations/${active.id}/documents/${id}`,null,{method:'DELETE'});setAttachedDocs(old=>old.filter(d=>d.id!==id));setSelectedDocs(old=>old.filter(d=>d!==id));setDocumentConsent(false);setDocumentNotice('Desanexado desta conversa; o arquivo continua na Biblioteca.');});}
 function openDocument(id,page=1){setDocumentPreview({id,page});}
 function startDocumentTask(title){if(title==='Analisar Arquivos'){uploadInput.current?.click();return;}setPlanned(title);}
 const historyProps={conversations,active,busy,hasMore,query,pinned,onPin:id=>setPinned(old=>old.includes(id)?old.filter(x=>x!==id):[...old,id]),onSelect:selectConversation,onDelete:setDeleteTarget,onMore:()=>perform(async()=>{const list=await api(`/conversations?offset=${conversations.length}&q=${encodeURIComponent(query)}`);setConversations(old=>[...old,...list]);setHasMore(list.length===100);})};
 const searchForm=<><form className="search-form" onSubmit={e=>{e.preventDefault();perform(async()=>{await refreshList(null,searchInput.trim());setQuery(searchInput.trim());});}}><Icon name="search" size={15}/><label className="sr-only" htmlFor="history-search">Buscar conversas</label><input id="history-search" placeholder="Buscar conversas…" value={searchInput} maxLength={200} onChange={e=>setSearchInput(e.target.value)} disabled={busy}/><button aria-label="Buscar" title="Buscar" disabled={busy}><Icon name="arrow" size={13}/></button></form>{query&&<button className="subtle clear-search" disabled={busy} onClick={()=>perform(async()=>{await refreshList(null,'');setQuery('');setSearchInput('');})}>Limpar busca</button>}</>;
 const pageTitle=navItems.find(n=>n[0]===view)?.[1]||'Aurora';
 return <div className={`app-shell ${navCollapsed?'nav-collapsed':''}`}>
 {checkingSession?<main className="login-screen"><p role="status">Verificando acesso…</p></main>:!authenticated?<main className="login-screen"><form onSubmit={login} className="login-card"><Mark/><p className="eyebrow">ASSISTENTE PESSOAL · V0.6.1</p><h1>Bem-vindo à Aurora.</h1><p className="muted">Um espaço para suas ideias, pesquisas e projetos.</p><label htmlFor="owner-token">Token do proprietário</label><input id="owner-token" type="password" autoComplete="current-password" required value={loginToken} onChange={e=>setLoginToken(e.target.value)} placeholder="Cole seu token de acesso"/><p className="hint">Use AURORA_OWNER_TOKEN de backend/.env. A chave Gemini fica somente no servidor.</p><label className="check-label"><input type="checkbox" checked={remember} onChange={e=>setRemember(e.target.checked)}/>Manter acesso por 7 dias neste dispositivo</label>{error&&<div role="alert" className="error">{error}</div>}<button className="primary" disabled={busy}>{busy?'Conectando…':'Entrar no meu espaço'}<Icon name="arrow"/></button><p className="hint">Use Sair para encerrar a sessão neste navegador.</p></form></main>:<>
 <aside ref={historyPanel} className={`rail ${sidebar?'open':''}`} aria-label="Menu da Aurora" inert={Boolean(deleteTarget||documentPreview)}><div className="rail-brand"><Mark/><span>Aurora<small>Sua assistente pessoal de IA</small></span><button className="mobile-close" aria-label="Fechar menu e histórico" onClick={()=>setSidebar(false)}><Icon name="close"/></button></div>
 {(historySide==='left'||compact)&&searchForm}<button className="new-chat" aria-label="Nova conversa" onClick={newConversation} disabled={busy}><Icon name="plus" size={17}/><span>Novo chat</span></button>
 <nav className="nav-items" aria-label="Navegação principal">{navItems.map(([id,title,icon])=><React.Fragment key={id}><div className="nav-row"><button className={view===id?'selected':''} aria-current={view===id?'page':undefined} aria-label={title} title={title} disabled={busy} onClick={()=>navigate(id)}><Icon name={icon} size={16}/><span>{title}</span></button>{id==='library'&&<button className="submenu-toggle" aria-label="Categorias da biblioteca" aria-expanded={libraryMenu} disabled={busy} onClick={()=>setLibraryMenu(!libraryMenu)}><Icon name="chevron" size={12}/></button>}</div>{id==='library'&&libraryMenu&&<div className="library-submenu">{['Todos','PDF','TXT'].map(f=><button key={f} disabled={busy} onClick={()=>{setLibraryFilter(f);navigate('library');}}>{f==='Todos'?'Todos os itens':f}</button>)}</div>}</React.Fragment>)}</nav>
 {(historySide==='left'||compact)&&<History {...historyProps}/>}
 <div className="profile"><span className="avatar">{(profile.name||'EU').slice(0,2).toUpperCase()}</span><span>{profile.name||'Meu espaço'}<small>Acesso pessoal</small></span><button aria-label="Sair" title="Sair" disabled={busy} onClick={logout}><Icon name="exit" size={16}/></button></div></aside>
 {sidebar&&compact&&<button className="sidebar-backdrop" tabIndex={-1} aria-label="Fechar menu" onClick={()=>setSidebar(false)}/>}
 <main className="workspace" inert={Boolean((sidebar&&compact)||deleteTarget||documentPreview)}><header className="topbar"><button ref={historyToggle} className="menu-toggle" aria-label={compact?'Abrir menu e histórico':navCollapsed?'Expandir barra lateral':'Recolher barra lateral'} aria-expanded={compact?sidebar:!navCollapsed} onClick={()=>compact?setSidebar(!sidebar):setNavCollapsed(!navCollapsed)}><Icon name="menu" size={19}/></button><span className="top-caption">{pageTitle}</span><span className="version">v0.6.1</span>{historySide==='right'&&!compact&&<button className="history-toggle" aria-label={rightOpen?'Recolher histórico':'Abrir histórico'} aria-expanded={rightOpen} onClick={()=>setRightOpen(!rightOpen)}><Icon name="chat" size={16}/><span>Histórico</span></button>}</header>
 {error&&<div role="alert" className="error global-error">{error}<button aria-label="Fechar erro" onClick={()=>setError('')}><Icon name="close" size={16}/></button></div>}
 <Suspense fallback={<p role="status" className="loading-module">Carregando…</p>}>
 {view==='chat'?<div className={`chat-page ${messages.length||sending||partialFailed?'has-messages':'is-home'}`}>
 {active&&messages.length>0&&<div className="conversation-toolbar"><span className="conversation-title" title={active.title}>{active.title}</span><button className="subtle" disabled={busy} onClick={()=>{setRenameValue(active.title);setRenaming(!renaming);}}>Renomear</button><button className="subtle" disabled={busy} onClick={()=>perform(()=>download(`/conversations/${active.id}/export?format=txt`,'aurora-conversa.txt'))}>Exportar TXT</button><button className="subtle" disabled={busy} onClick={()=>perform(()=>download(`/conversations/${active.id}/export?format=json`,'aurora-conversa.json'))}>Exportar JSON</button></div>}
 {renaming&&active&&<form className="rename-form" onSubmit={e=>{e.preventDefault();perform(async()=>{const updated=await api(`/conversations/${active.id}`,null,{method:'PATCH',body:JSON.stringify({title:renameValue})});setActive(updated);setRenaming(false);await refreshList();});}}><label className="sr-only" htmlFor="conversation-title">Título da conversa</label><input id="conversation-title" className="text-input" value={renameValue} maxLength={120} onChange={e=>setRenameValue(e.target.value)} disabled={busy}/><button className="subtle" disabled={busy||!renameValue.trim()}>Salvar título</button><button type="button" className="subtle" onClick={()=>setRenaming(false)} disabled={busy}>Cancelar</button></form>}
 <div className="conversation-scroll">{messages.length===0&&!sending&&!partialFailed?<Home name={profile.name} onPrompt={prompt} onPlanned={startDocumentTask} onAgents={openAgents} busy={busy} configured={config.configured}/>:<section className="messages" aria-label="Mensagens">{nextBefore&&<button className="subtle" disabled={busy} onClick={()=>perform(async()=>{const data=await api(`/conversations/${active.id}?before=${nextBefore}`);setMessages(old=>[...data.messages,...old]);setNextBefore(data.next_before);})}>Carregar mensagens anteriores</button>}{messages.map(message=><article className={`message ${message.role}`} key={message.id}><div className="message-label">{message.role==='assistant'?<><Mark small/>Aurora</>:<><span className="tiny-avatar">EU</span>Você</>}{message.role==='assistant'&&<span className="message-model">{message.model}</span>}<time>{new Date(message.created_at).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'})}</time></div><div className="message-content">{message.role==='assistant'?<ResponseContent text={message.content}/>:message.content}</div>{message.role==='assistant'&&<div className="response-actions"><CopyButton text={message.content}/>{message.id===messages.at(-1)?.id&&<details className="response-more"><summary>Mais opções</summary><button className="subtle" disabled={busy} onClick={()=>prompt('Resuma sua última resposta.')}>Resumir</button><button className="subtle" disabled={busy} onClick={()=>prompt('Explique com mais detalhes sua última resposta.')}>Detalhar</button><button className="subtle" disabled={busy} onClick={()=>prompt('Continue sua última resposta de onde parou.')}>Continuar</button></details>}{message.workspace&&<span className="hint">{message.workspace.profile_name}{message.workspace.project_name?' · '+message.workspace.project_name:''}</span>}</div>}{message.documents_used?.length>0&&<div className="message-document-info"><p>Documentos enviados nesta pergunta: {message.documents_used.map(d=>d.name).join(', ')}</p>{message.sources?.length>0&&<div className="message-sources"><span>Referências indicadas pelo modelo:</span>{message.sources.map(source=><button className="subtle" key={`${source.document_id}-${source.page}`} disabled={!source.available} onClick={()=>openDocument(source.document_id,source.page)}>{source.name} · p. {source.page}{!source.available?' (excluído)':''}</button>)}</div>}{message.source_warning&&<p className="source-warning">{message.source_warning}</p>}<p className="hint">As referências apontam para páginas enviadas; confira se o texto sustenta a resposta.</p></div>}</article>)}</section>}{(sending||partialFailed)&&<section className="live-response" aria-label="Resposta em andamento">{pendingQuestion&&<p className="pending-question">{pendingQuestion}</p>}{partial&&<><div className="message-label"><Mark small/>Aurora <span className="hint">{partialFailed?'Resposta incompleta':'Respondendo'}</span></div><div className="stream-text">{partial}</div></>}{sending&&<p role="status" className="thinking">{sendStage||'Aguardando resposta…'}</p>}{partialFailed&&<p className="source-warning">O trecho acima ficou incompleto e não foi salvo no histórico. Sua pergunta permanece no campo para revisão.</p>}</section>}<div ref={end}/></div>
 <div className="composer-wrap">{modelNotice&&<p role="status" className="fallback-notice">{modelNotice}</p>}{planned&&<div className="planned-notice" role="status"><Icon name="tools" size={16}/><span>{planned} está em desenvolvimento. Nesta versão, o chat recebe texto e anexos PDF/TXT com texto extraível.</span><button aria-label="Fechar aviso" onClick={()=>setPlanned('')}><Icon name="close" size={14}/></button></div>}{!config.configured&&<p className="setup-notice">Configure a chave e o modelo no servidor para conversar. Veja Configurações → Modelos de IA.</p>}
 <ContextPanel key={active?.id||'new'} context={chatContext} profiles={profiles} projects={projects} memories={memories} active={active} busy={busy} run={perform} onChange={changes=>perform(()=>changeContext(changes))} onReload={async()=>setChatContext(await api(`/conversations/${active.id}/context`))} model={model} documentCount={selectedDocs.length} onManage={()=>{setManagerTab('memories');navigate('organization');}}/>
 <ConversationDocuments documents={attachedDocs} selected={selectedDocs} consent={documentConsent} onConsent={value=>{setDocumentConsent(value);setDocumentNotice('');}} onSelect={selectDocument} onPreview={openDocument} onDetach={detachDocument} onLibrary={()=>navigate('library')} busy={busy} notice={documentNotice}/><input ref={uploadInput} type="file" className="sr-only" aria-label="Anexar PDF ou TXT ao chat" accept=".pdf,.txt,application/pdf,text/plain" disabled={busy} onChange={e=>{const file=e.target.files[0];e.target.value='';uploadToConversation(file);}}/><form className="composer" onSubmit={send}><label className="sr-only" htmlFor="message">Sua mensagem</label><textarea ref={input} id="message" placeholder="Digite sua mensagem aqui…" maxLength={8000} value={draft} disabled={busy} onChange={e=>setDraft(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();send(e);}}} rows={2}/><div className="composer-bottom"><div className="composer-tools"><button type="button" aria-label="Anexar PDF ou TXT" title="Anexar PDF ou TXT" disabled={busy} onClick={()=>uploadInput.current?.click()}><Icon name="plus" size={16}/></button>{[['Arquivos','file'],['Imagem','image'],['Pesquisa','search']].map(([title,icon])=><button type="button" className="composer-tool" key={title} aria-label={title} title={title==='Arquivos'?'Anexar PDF ou TXT':'Em desenvolvimento'} disabled={busy} onClick={()=>title==='Arquivos'?uploadInput.current?.click():setPlanned(title)}><Icon name={icon} size={13}/><span>{title}</span></button>)}<button type="button" className="composer-tool" onClick={()=>navigate('tools')}><Icon name="tools" size={13}/><span>Ferramentas</span></button></div><div className="model-choice"><Icon name="spark" size={15}/><label className="sr-only" htmlFor="model">Modelo Gemini</label><select id="model" value={model} onChange={e=>setModel(e.target.value)} disabled={busy||!config.models.length}>{config.models.length?config.models.map(m=><option key={m}>{m}</option>):<option value="">Gemini · não configurado</option>}</select></div><button className="send-button" type="submit" aria-label="Enviar mensagem" disabled={busy||!draft.trim()||!config.configured||(selectedDocs.length>0&&!documentConsent)}><Icon name="send" size={20}/></button></div></form>
 {messages.length===0&&<QuickActions onPrompt={prompt} busy={busy}/>}<p className="composer-note">{draftWarning||'Rascunho salvo neste navegador. Aurora pode cometer erros.'}<span> Enter envia · Shift + Enter quebra linha</span></p></div></div>:
 view==='agents'?<Agents items={profiles} run={perform} busy={busy} onReload={reloadWorkspace} onUse={id=>perform(async()=>{await changeContext({profile_id:id});navigate('chat');})}/>:
 view==='library'?<Library key={libraryFilter} initial={libraryFilter} run={perform} busy={busy} onPreview={openDocument} onAttach={attachDocument} onDeleted={documentDeleted} active={active}/>:
 view==='plugins'||view==='tools'?<Tools key={view} plugins={view==='plugins'}/>:
 view==='computer'?<Computer/>:
 view==='organization'?<WorkspaceManager key={managerTab} initial={managerTab} projects={projects} memories={memories} conversations={conversations} run={perform} busy={busy} onReload={reloadWorkspace} onOpen={selectConversation} onNew={newConversation} onPreview={openDocument} onAttach={attachDocument}/>:
 <SettingsPanel fallbackEnabled={fallbackEnabled} onFallback={setFallbackEnabled} tab={settingsTab} onTab={setSettingsTab} theme={theme} onTheme={setTheme} accent={accent} onAccent={setAccent} effects={effects} onEffects={setEffects} historySide={historySide} onHistorySide={setHistorySide} config={config} model={model} onModel={setModel} run={perform} busy={busy} profile={profile} onPreferences={setProfile} onLogout={logout} onConfig={async()=>{const cfg=await api('/config');setConfig(cfg);setModel(cfg.models.includes(model)?model:chooseModel(cfg));}} onRestored={async()=>{try{localStorage.removeItem('aurora-drafts-'+config.workspace_id);}catch{}selectDraft(null);setChatContext(null);const [ps,pj,ms]=await Promise.all([api('/profiles'),api('/projects'),api('/memories')]);setProfiles(ps);setProjects(pj);setMemories(ms);setAttachedDocs([]);setSelectedDocs([]);setDocumentConsent(false);setDocumentNotice('');setModelNotice('');setActive(null);setMessages([]);setDraft('');setNextBefore(null);setAttachedDocs([]);setSelectedDocs([]);setDocumentConsent(false);retry.current=null;setQuery('');setSearchInput('');setRenaming(false);await refreshList(null,'');const prefs=await api('/preferences');setProfile(prefs.saved||{name:''});}}/>}
 </Suspense></main>
 {historySide==='right'&&!compact&&rightOpen&&<aside className="right-history" aria-label="Painel direito de conversas" inert={Boolean(deleteTarget||documentPreview)}><div className="right-history-heading"><h2>Conversas</h2><button aria-label="Recolher histórico" onClick={()=>setRightOpen(false)}><Icon name="close" size={16}/></button></div>{searchForm}<History {...historyProps}/></aside>}
 {deleteTarget&&<div className="modal-backdrop" onKeyDown={e=>{if(e.key==='Escape'&&!busy)setDeleteTarget(null);if(e.key==='Tab'){const elements=[...e.currentTarget.querySelectorAll('button:not(:disabled)')];if(!elements.length){e.preventDefault();return;}const first=elements[0],last=elements[elements.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}}}><section role="dialog" aria-modal="true" aria-labelledby="delete-title" className="modal"><h2 id="delete-title">Excluir esta conversa?</h2>{error&&<p role="alert" className="error">{error}</p>}<p>“{deleteTarget.title}” e suas mensagens serão apagadas. Esta ação não pode ser desfeita.</p><div className="action-row"><button id="cancel-delete" className="subtle" disabled={busy} onClick={()=>setDeleteTarget(null)}>Cancelar</button><button className="danger" disabled={busy} onClick={()=>perform(async()=>{await api(`/conversations/${deleteTarget.id}?confirm=true`,null,{method:'DELETE'});forgetDraft(deleteTarget.id);setConversations(old=>old.filter(c=>c.id!==deleteTarget.id));if(active?.id===deleteTarget.id){setActive(null);setMessages([]);selectDraft(null);setChatContext(null);setNextBefore(null);setAttachedDocs([]);setSelectedDocs([]);setDocumentConsent(false);retry.current=null;}setDeleteTarget(null);})}>Excluir conversa</button></div></section></div>}
 {documentPreview&&<Suspense fallback={<div className="modal-backdrop"><p role="status">Carregando prévia…</p></div>}><DocumentPreview key={`${documentPreview.id}-${documentPreview.page}`} id={documentPreview.id} initialPage={documentPreview.page} onClose={()=>setDocumentPreview(null)}/></Suspense>}
 </>}
 </div>;
}
