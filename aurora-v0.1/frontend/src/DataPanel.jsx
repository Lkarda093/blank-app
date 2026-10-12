import React, { useEffect, useState } from 'react';
import { api, download } from './api.js';
export default function DataPanel({ run, busy, onRestored }) {
  const [stats, setStats] = useState(null);
  const [recovery, setRecovery] = useState([]);
  const [candidate, setCandidate] = useState(null);
  const [preview, setPreview] = useState(null);
  const [confirmation, setConfirmation] = useState('');
  const [consent, setConsent] = useState(false);
  const [notice, setNotice] = useState('');
  async function reload() { const [a,b] = await Promise.all([api('/data/stats'),api('/data/recovery')]); setStats(a); setRecovery(b); }
  useEffect(() => { run(reload); }, []);
  async function inspect(text) { const result = await api('/data/restore/preview',null,{method:'POST',body:text}); setPreview(result); setConfirmation(''); setConsent(false); }
  return <>
    <div className="settings-card"><h2>Seus dados</h2>{stats ? <p className="muted">{stats.conversations} conversas · {stats.turns} pares de mensagens · {stats.preferences_saved ? 'preferências salvas' : 'sem preferências salvas'}</p> : <p className="hint">Carregando dados…</p>}
      <p className="muted">Baixe uma cópia completa das conversas e preferências. Guarde o arquivo fora do Codespace.</p><button className="subtle" disabled={busy} onClick={() => run(() => download('/data/backup','aurora-backup.json'))}>Baixar backup completo</button><p className="hint">JSON portátil, até 16 MiB. Chaves, token de acesso e sessões não entram no backup. O arquivo contém suas conversas e preferências sem criptografia.</p>
    </div>
    <div className="settings-card"><h2>Restaurar backup</h2><p className="muted">A restauração substitui todas as conversas e preferências atuais pelos dados do arquivo escolhido.</p>
      {notice && <p role="status" className="success">{notice}</p>}
      <label className="field-label" htmlFor="backup-file">Backup completo da Aurora 0.2 (.json)</label><input className="text-input" id="backup-file" type="file" accept=".json,application/json" disabled={busy} onChange={event => { const file=event.target.files[0]; setPreview(null); setCandidate(null); setNotice(''); setConfirmation(''); setConsent(false); if (!file) return; run(async () => { if(file.size>16*1024*1024) throw new Error('O arquivo deve ter no máximo 16 MiB.'); const text=await file.text(); setCandidate({text,name:file.name}); await inspect(text); }); }} />
      {preview && <div className="restore-preview"><h3>Confira antes de restaurar</h3><p>Atualmente: <strong>{preview.current.conversations} conversas e {preview.current.turns} pares de mensagens.</strong></p><p>No arquivo: <strong>{preview.conversations} conversas e {preview.turns} pares de mensagens.</strong></p>
        {preview.preferences ? <><p>Preferências incluídas:</p><pre>{JSON.stringify(preview.preferences,null,2)}</pre><label className="check-label"><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} disabled={busy} />Autorizo restaurar estas preferências e usá-las nas próximas respostas.</label></> : <p>O arquivo não contém preferências; as preferências atuais serão apagadas.</p>}
        <p className="hint">Antes de substituir os dados, Aurora guarda uma cópia de recuperação no servidor. Nenhuma alteração é feita até você confirmar abaixo.</p>
        <label className="field-label" htmlFor="restore-confirm">Digite RESTAURAR para confirmar</label><input id="restore-confirm" className="text-input" value={confirmation} onChange={e => setConfirmation(e.target.value)} autoComplete="off" disabled={busy} />
        <div className="action-row"><button className="danger" disabled={busy || confirmation!=='RESTAURAR' || (preview.preferences && !consent)} onClick={() => run(async () => { await api('/data/restore',null,{method:'POST',body:candidate.text,headers:{'X-Aurora-Confirm':confirmation,'X-Aurora-Revision':String(preview.expected_revision),'X-Aurora-Preview':preview.ticket,'X-Aurora-Preferences-Consent':consent?'1':'0'}}); setCandidate(null); setPreview(null); setConfirmation(''); setConsent(false); setNotice('Backup restaurado. A cópia anterior está disponível abaixo.'); await onRestored(); await reload(); })}>Confirmar restauração</button><button className="subtle" disabled={busy} onClick={() => run(() => inspect(candidate.text))}>Atualizar prévia</button><button className="subtle" disabled={busy} onClick={() => {setCandidate(null);setPreview(null);setConfirmation('');setConsent(false);}}>Cancelar</button></div>
      </div>}
    </div>
    <div className="settings-card"><h2>Cópias anteriores à restauração</h2><p className="hint">Para desfazer uma restauração, baixe a cópia anterior e selecione esse arquivo no formulário acima. As 20 cópias mais recentes aparecem aqui; arquivos mais antigos permanecem na pasta de backups do servidor.</p>{recovery.length ? recovery.map(item => <div className="recovery-row" key={item.id}><time>{new Date(item.created_at).toLocaleString('pt-BR')}</time><button className="subtle" disabled={busy} onClick={() => run(() => download(`/data/recovery/${item.id}`,`aurora-recuperacao-${item.id}.json`))}>Baixar cópia</button></div>) : <p className="hint">Nenhuma restauração foi realizada.</p>}</div>
  </>;
}
