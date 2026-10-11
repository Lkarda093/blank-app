import React, { useEffect, useRef, useState } from 'react';
import { api } from './api.js';

function Icon({ name, size = 20 }) {
  const paths = {
    chat: 'M4 4h16v12H9l-5 4V4Z', plus: 'M12 5v14M5 12h14',
    send: 'm5 12 7-7 7 7M12 5v15', sun: 'M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1 1M18 18l1 1M5 19l1-1M18 6l1-1M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
    settings: 'M4 6h16M4 12h16M4 18h16M8 3v6M16 9v6M10 15v6',
    shield: 'm12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Zm-4 9 3 3 5-6',
    menu: 'M4 6h16M4 12h16M4 18h16', trash: 'M3 6h18M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7M14 10v7',
    exit: 'M9 4H4v16h5M9 12h12m-5-5 5 5-5 5', close: 'm6 6 12 12M6 18 18 6',
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.chat} /></svg>;
}
function Mark({ small = false }) { return <span className={`mark ${small ? 'small' : ''}`} aria-hidden="true"><i /><i /><i /></span>; }

export default function App() {
  const [theme, setTheme] = useState(() => { try { return localStorage.getItem('aurora-theme') || 'dark'; } catch { return 'dark'; } });
  const [token, setToken] = useState('');
  const [loginToken, setLoginToken] = useState('');
  const [config, setConfig] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [hasMore, setHasMore] = useState(false);
  const [active, setActive] = useState(null);
  const [messages, setMessages] = useState([]);
  const [nextBefore, setNextBefore] = useState(null);
  const [draft, setDraft] = useState('');
  const [model, setModel] = useState('');
  const [busy, setBusy] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [view, setView] = useState('chat');
  const [sidebar, setSidebar] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const retry = useRef(null);
  const end = useRef(null);
  const input = useRef(null);
  const gate = useRef(false);
  useEffect(() => { document.documentElement.dataset.theme = theme; try { localStorage.setItem('aurora-theme', theme); } catch {} }, [theme]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'auto' }); }, [active, sending]);
  useEffect(() => { if (deleteTarget) document.getElementById('cancel-delete')?.focus(); }, [deleteTarget]);

  async function perform(work) {
    if (gate.current) return;
    gate.current = true; setBusy(true); setError('');
    try { await work(); } catch (e) { setError(e.message); }
    finally { gate.current = false; setBusy(false); }
  }
  async function refreshList(auth = token) {
    const list = await api('/conversations', auth);
    setConversations(list); setHasMore(list.length === 100);
  }
  async function login(event) {
    event.preventDefault();
    await perform(async () => {
      const auth = loginToken.trim();
      const [cfg, list] = await Promise.all([api('/config', auth), api('/conversations', auth)]);
      setConfig(cfg); setModel(cfg.models[0] || ''); setConversations(list); setHasMore(list.length === 100);
      setToken(auth); setLoginToken('');
    });
  }
  async function selectConversation(id) {
    await perform(async () => {
      const data = await api(`/conversations/${id}`, token);
      setActive(data); setMessages(data.messages); setNextBefore(data.next_before);
      setDraft(''); retry.current = null; setView('chat'); setSidebar(false);
    });
  }
  async function newConversation() {
    await perform(async () => {
      const data = await api('/conversations', token, { method: 'POST' });
      setActive(data); setMessages([]); setNextBefore(null); setDraft(''); retry.current = null;
      setConversations(old => [data, ...old]); setView('chat'); setSidebar(false);
    });
  }
  async function send(event) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || !config?.configured || !model) return;
    await perform(async () => {
      setSending(true);
      try {
        let conversation = active;
        if (!conversation) {
          conversation = await api('/conversations', token, { method: 'POST' });
          setActive(conversation); setConversations(old => [conversation, ...old]);
        }
        if (!retry.current || retry.current.content !== text || retry.current.model !== model || retry.current.cid !== conversation.id) {
          retry.current = { content: text, model, cid: conversation.id, request_id: crypto.randomUUID() };
        }
        const { cid, ...payload } = retry.current;
        const result = await api(`/conversations/${cid}/messages`, token, { method: 'POST', body: JSON.stringify(payload) });
        setMessages(old => [...old.filter(m => !result.messages.some(n => n.id === m.id)), ...result.messages]);
        setDraft(''); retry.current = null;
        setActive(old => ({ ...old, title: old.title === 'Nova conversa' ? text.slice(0, 60) : old.title }));
        await refreshList();
        setTimeout(() => { end.current?.scrollIntoView({ behavior: 'smooth' }); input.current?.focus(); }, 0);
      } finally { setSending(false); }
    });
  }
  function logout() {
    setToken(''); setConfig(null); setConversations([]); setMessages([]); setActive(null);
    setDraft(''); setError(''); setView('chat'); setDeleteTarget(null); retry.current = null;
  }
  const pageTitle = view === 'chat' ? 'Seu espaço de ideias' : view === 'settings' ? 'Configurações' : 'Painel do proprietário';
  return <div className="app-shell">
    {!token ? <main className="login-screen"><form onSubmit={login} className="login-card">
      <Mark /><p className="eyebrow">ASSISTENTE PESSOAL · V0.1</p><h1>Bem-vindo à Aurora.</h1>
      <p className="muted">Um espaço tranquilo para pensar, conversar e construir.</p>
      <label htmlFor="owner-token">Token do proprietário</label>
      <input id="owner-token" type="password" autoComplete="current-password" required value={loginToken} onChange={e => setLoginToken(e.target.value)} placeholder="Cole seu token de acesso" />
      <p className="hint">Use AURORA_OWNER_TOKEN de backend/.env. A chave Gemini fica somente no servidor.</p>
      {error && <div role="alert" className="error">{error}</div>}
      <button className="primary" disabled={busy}>{busy ? 'Conectando…' : 'Entrar no meu espaço'} <span aria-hidden="true">↗</span></button>
      <p className="hint">O token é mantido somente na memória desta página. Ao recarregar, entre novamente.</p>
    </form></main> : <>
      <nav className="rail" aria-label="Navegação principal"><div className="rail-brand"><Mark small /></div>
        <button className={view === 'chat' ? 'selected' : ''} aria-label="Conversar" title="Conversar" onClick={() => setView('chat')} disabled={busy}><Icon name="chat" /></button>
        <button className={view === 'settings' ? 'selected' : ''} aria-label="Configurações" title="Configurações" onClick={() => setView('settings')} disabled={busy}><Icon name="settings" /></button>
        <button className={view === 'admin' ? 'selected' : ''} aria-label="Administração" title="Administração" onClick={() => setView('admin')} disabled={busy}><Icon name="shield" /></button>
        <div className="rail-spacer" /><button aria-label="Alternar tema" title="Alternar tema" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}><Icon name="sun" /></button>
        <button aria-label="Sair" title="Sair" onClick={logout} disabled={busy}><Icon name="exit" /></button><span className="avatar">EU</span>
      </nav>
      <main className="workspace">
        <header className="topbar"><div><span className="brand">aurora<span className="brand-dot">.</span></span><span className="top-caption">{pageTitle}</span></div>
          <div className="flex items-center gap-3"><span className="version">v0.1</span><button className="mobile-menu" aria-label="Abrir histórico" onClick={() => setSidebar(!sidebar)}><Icon name="menu" /></button></div>
        </header>
        {error && <div role="alert" className="error global-error">{error}<button aria-label="Fechar erro" onClick={() => setError('')}><Icon name="close" size={16} /></button></div>}
        {view === 'chat' ? <>
          <div className="conversation-scroll">
            {messages.length === 0 ? <section className="welcome"><div className="welcome-orbit"><Mark /></div><p className="eyebrow">UM PENSAMENTO É UM COMEÇO</p><h1>O que vamos<br /><em>construir hoje?</em></h1><p className="muted">Traga uma pergunta, uma ideia ou um plano.<br />Vamos dar o próximo passo juntos.</p>
              <div className="suggestions">{[['Organizar uma ideia', 'Ajude-me a organizar uma ideia. Comece perguntando o que pretendo desenvolver.'], ['Entender um assunto', 'Quero entender um assunto de forma simples. Pergunte qual é o tema.'], ['Planejar meu dia', 'Ajude-me a planejar meu dia. Pergunte quais são minhas prioridades.']].map(([title, text], i) => <button key={title} disabled={busy} onClick={() => { setDraft(text); input.current?.focus(); }}><span className="suggestion-index">0{i + 1}</span>{title}<span aria-hidden="true">↗</span></button>)}</div>
            </section> : <section className="messages" aria-label="Mensagens">
              {nextBefore && <button className="subtle" disabled={busy} onClick={() => perform(async () => { const data = await api(`/conversations/${active.id}?before=${nextBefore}`, token); setMessages(old => [...data.messages, ...old]); setNextBefore(data.next_before); })}>Carregar mensagens anteriores</button>}
              {messages.map(message => <article className={`message ${message.role}`} key={message.id}><div className="message-label">{message.role === 'assistant' ? <><Mark small /> Aurora</> : <><span className="tiny-avatar">EU</span> Você</>}<time>{new Date(message.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</time></div><div className="message-content">{message.content}</div></article>)}
            </section>}
            {sending && <p role="status" className="thinking">Aurora está preparando uma resposta<span className="pulse">…</span></p>}<div ref={end} />
          </div>
          <div className="composer-wrap">{!config.configured && <p className="setup-notice">Para conversar, preencha GEMINI_API_KEY e GEMINI_MODELS em backend/.env e reinicie o backend.</p>}
            <form className="composer" onSubmit={send}><label className="sr-only" htmlFor="message">Sua mensagem</label><textarea ref={input} id="message" placeholder="Escreva para Aurora…" maxLength={8000} value={draft} disabled={busy} onChange={e => setDraft(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(e); } }} rows={3} />
              <div className="composer-bottom"><div className="model-choice"><span className="status-dot" /><label className="sr-only" htmlFor="model">Modelo Gemini</label><select id="model" value={model} onChange={e => setModel(e.target.value)} disabled={busy || !config.models.length}>{config.models.length ? config.models.map(m => <option key={m}>{m}</option>) : <option value="">Gemini · não configurado</option>}</select></div><span className="char-count">{draft.length}/8.000</span><button className="send-button" type="submit" aria-label="Enviar mensagem" disabled={busy || !draft.trim() || !config.configured}><Icon name="send" /></button></div>
            </form><p className="composer-note">Aurora pode cometer erros. Confira informações importantes. <span>Enter envia · Shift + Enter quebra linha</span></p>
          </div>
        </> : <section className="settings-page"><p className="eyebrow">SEU ESPAÇO, SEU CONTROLE</p><h1>{pageTitle}</h1>
          {view === 'settings' ? <><div className="settings-card"><h2>Aparência</h2><p className="muted">Preferência salva neste navegador.</p><button className="subtle" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>Tema atual: {theme === 'dark' ? 'escuro' : 'claro'} · alternar</button></div>
            <div className="settings-card"><h2>Conexão com Gemini</h2><p>{config.configured ? 'Chave e modelos configurados no servidor.' : 'Configuração incompleta no servidor.'}</p><p className="hint">Configuração detectada não comprova que a chave é válida. O primeiro envio verifica o acesso real.</p><p className="muted">Edite backend/.env e reinicie o FastAPI para alterar a chave ou a lista GEMINI_MODELS. Segredos não são exibidos aqui.</p><button className="subtle" disabled={busy} onClick={() => perform(async () => { const cfg = await api('/config', token); setConfig(cfg); setModel(cfg.models.includes(model) ? model : cfg.models[0] || ''); })}>Atualizar status</button></div>
            <div className="settings-card"><h2>Cotas e privacidade</h2><p className="muted">{config.cost_notice}</p><p className="muted">Sua mensagem e até 10 interações anteriores desta conversa são enviadas ao Google. O contexto tem limite de 40.000 caracteres; o histórico completo permanece no servidor.</p><a href="https://ai.google.dev/gemini-api/docs/pricing" target="_blank" rel="noreferrer">Consultar preços e condições ↗</a></div></> : <>
            <div className="settings-card"><h2>Instância pessoal</h2><dl><div><dt>Versão</dt><dd>{config.version}</dd></div><div><dt>Acesso</dt><dd>Proprietário · token</dd></div><div><dt>Histórico</dt><dd>SQLite no servidor</dd></div><div><dt>Provedor implementado</dt><dd>Gemini</dd></div></dl></div>
            <div className="settings-card"><h2>Gerenciamento nesta versão</h2><p className="muted">Crie e exclua conversas pelo histórico. Configure segredos no arquivo backend/.env. O README explica backup e recuperação manual com o servidor parado.</p><p className="hint">Banco sem criptografia própria. Proteja sua conta, o computador e os arquivos de backup.</p></div>
            <div className="settings-card"><h2>Expansões planejadas</h2><p className="muted">Memórias editáveis, documentos, Obsidian, plugins, voz, outros provedores e agente local ainda não estão implementados. Não há aprendizado autônomo nem acesso ao seu computador.</p></div>
          </>}
        </section>}
      </main>
      {sidebar && <button className="sidebar-backdrop" aria-label="Fechar histórico" onClick={() => setSidebar(false)} />}
      <aside className={`sidebar ${sidebar ? 'open' : ''}`} aria-label="Histórico de conversas"><div className="sidebar-heading"><span>MEU ESPAÇO</span><button className="mobile-menu" aria-label="Fechar histórico" onClick={() => setSidebar(false)}><Icon name="close" /></button><span className="owner-badge">Pessoal</span></div><button className="new-chat" onClick={newConversation} disabled={busy}><Icon name="plus" size={18} /> Nova conversa</button>
        <div className="history-heading"><h2>Conversas</h2><span>{conversations.length}{hasMore ? '+' : ''}</span></div>
        <div className="history-list">{conversations.length === 0 ? <p className="hint empty-history">Seu histórico começa com a primeira conversa.</p> : conversations.map(c => <div className={`history-item ${active?.id === c.id ? 'active' : ''}`} key={c.id}><button className="history-select" disabled={busy} onClick={() => selectConversation(c.id)} title={c.title}><Icon name="chat" size={15} /><span>{c.title}</span></button><button className="delete-button" disabled={busy} aria-label={`Excluir ${c.title}`} onClick={() => setDeleteTarget(c)}><Icon name="trash" size={15} /></button></div>)}
          {hasMore && <button className="subtle" disabled={busy} onClick={() => perform(async () => { const list = await api(`/conversations?offset=${conversations.length}`, token); setConversations(old => [...old, ...list]); setHasMore(list.length === 100); })}>Carregar mais</button>}
        </div><div className="roadmap"><span className="eyebrow">PRÓXIMOS CAPÍTULOS</span><p>Biblioteca & plugins</p><span className="hint">Planejados · ainda indisponíveis</span></div><div className="sidebar-footer"><span className="status-dot" /><span>Histórico salvo no servidor</span></div>
      </aside>
      {deleteTarget && <div className="modal-backdrop" onKeyDown={e => {
        if (e.key === 'Escape' && !busy) setDeleteTarget(null);
        if (e.key === 'Tab') { const elements = [...e.currentTarget.querySelectorAll('button:not(:disabled)')]; if (!elements.length) { e.preventDefault(); return; } const first = elements[0], last = elements[elements.length - 1]; if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); } else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); } }
      }}><section role="dialog" aria-modal="true" aria-labelledby="delete-title" className="modal"><h2 id="delete-title">Excluir esta conversa?</h2><p>“{deleteTarget.title}” e suas mensagens serão apagadas. Esta ação não pode ser desfeita.</p><div className="flex justify-end gap-3"><button id="cancel-delete" className="subtle" disabled={busy} onClick={() => setDeleteTarget(null)}>Cancelar</button><button className="danger" disabled={busy} onClick={() => perform(async () => { await api(`/conversations/${deleteTarget.id}?confirm=true`, token, { method: 'DELETE' }); setConversations(old => old.filter(c => c.id !== deleteTarget.id)); if (active?.id === deleteTarget.id) { setActive(null); setMessages([]); setDraft(''); setNextBefore(null); retry.current = null; } setDeleteTarget(null); })}>Excluir conversa</button></div></section></div>}
    </>}
  </div>;
}
