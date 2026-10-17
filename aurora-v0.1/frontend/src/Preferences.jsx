import React, { useEffect, useState } from 'react';
import { api, saveFile } from './api.js';
const empty = { name: '', response_style: 'equilibrado', notes: '' };
export default function Preferences({ run, busy, onSaved = () => {} }) {
  const [values, setValues] = useState(empty);
  const [saved, setSaved] = useState(null);
  const [consent, setConsent] = useState(false);
  const [ready, setReady] = useState(false);
  const [notice, setNotice] = useState('');
  const [loadError, setLoadError] = useState('');
  useEffect(() => { let alive = true; api('/preferences').then(data => { if(alive) {setValues(data.saved || empty);setSaved(data.saved);setReady(true);} }).catch(error => {if(alive) setLoadError(error.message);}); return () => {alive=false;}; }, []);
  function change(key, value) { setValues(old => ({ ...old, [key]: value })); setConsent(false); setNotice(''); }
  return <div className="settings-card"><h2>Preferências pessoais</h2><p className="muted">Você decide o que Aurora lembra entre conversas. As informações salvas abaixo serão enviadas ao modelo selecionado junto das próximas mensagens.</p>
    {loadError && <p role="alert" className="error">{loadError}</p>}{notice && <p role="status" className="success">{notice}</p>}
    <form onSubmit={event => { event.preventDefault(); run(async () => { const result = await api('/preferences', null, {method:'PUT',body:JSON.stringify({...values,consent})}); setSaved(result.saved); onSaved(result.saved); setValues(result.saved); setConsent(false); setNotice('Preferências salvas. Serão usadas a partir da próxima mensagem.'); }); }}>
      <label className="field-label" htmlFor="pref-name">Como você quer ser chamado?</label><input id="pref-name" className="text-input" value={values.name} maxLength={80} onChange={e => change('name',e.target.value)} disabled={!ready || busy} />
      <label className="field-label" htmlFor="pref-style">Estilo de resposta</label><select id="pref-style" className="text-input" value={values.response_style} onChange={e => change('response_style',e.target.value)} disabled={!ready || busy}><option value="equilibrado">Equilibrado</option><option value="conciso">Curto e direto</option><option value="detalhado">Detalhado e explicativo</option></select>
      <label className="field-label" htmlFor="pref-notes">Outras preferências ({values.notes.length}/1.000)</label><textarea id="pref-notes" className="text-input" rows={3} maxLength={1000} placeholder="Ex.: explique termos técnicos com exemplos simples." value={values.notes} onChange={e => change('notes',e.target.value)} disabled={!ready || busy} />
      <label className="check-label"><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} disabled={!ready || busy} />Autorizo salvar estas preferências e enviá-las ao provedor nas próximas mensagens.</label>
      <div className="action-row"><button className="subtle" disabled={!ready || busy || !consent}>Salvar e usar preferências</button><button type="button" className="subtle" disabled={busy || !saved} onClick={() => saveFile(new Blob([JSON.stringify(saved,null,2)],{type:'application/json'}),'aurora-preferencias.json')}>Exportar preferências</button><button type="button" className="danger" disabled={busy || !saved} onClick={() => { if (window.confirm('Apagar suas preferências salvas? Elas deixarão de ser enviadas nas próximas mensagens. O histórico de conversas e os backups existentes continuam guardados.')) run(async () => { await api('/preferences?confirm=true',null,{method:'DELETE'}); setSaved(null); onSaved(empty); setValues(empty); setConsent(false); setNotice('Preferências apagadas.'); }); }}>Apagar preferências</button></div>
    </form>
    <p className="hint">Nenhuma preferência é extraída automaticamente do chat. Alterar ou apagar preferências não modifica respostas anteriores nem cópias de backup.</p>
  </div>;
}
