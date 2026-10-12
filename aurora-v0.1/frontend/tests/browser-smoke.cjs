/* Optional browser QA. Uses test-only backend; never a real Gemini key. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
(async () => {
  const binary = process.env.AURORA_TEST_CHROMIUM;
  const browser = await chromium.launch({headless:true, ...(binary ? {executablePath:binary,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']} : {})});
  const directory = await fs.mkdtemp(path.join(os.tmpdir(),'aurora-browser-downloads-'));
  const context = await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce',acceptDownloads:true});
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  async function click(name) { await page.getByRole('button',{name,exact:true}).click(); }
  async function send(text) { await page.getByLabel('Sua mensagem',{exact:true}).fill(text);await click('Enviar mensagem');await page.getByText('RESPOSTA SIMULADA DE TESTE: '+text,{exact:true}).waitFor(); }
  async function download(name, filename) {const pending=page.waitForEvent('download');await click(name);const item=await pending;const file=path.join(directory,filename);await item.saveAs(file);return file;}
  async function waitEnabled(name) {await page.getByRole('button',{name,exact:true}).waitFor(); await page.waitForFunction(label => [...document.querySelectorAll('button')].some(b=>b.textContent.trim()===label && !b.disabled),name);}
  try {
    await page.goto('http://127.0.0.1:5173');
    await page.getByLabel('Token do proprietário',{exact:true}).fill('wrong');await click('Entrar no meu espaço');
    await page.getByRole('alert').filter({hasText:'Token do proprietário inválido'}).waitFor();
    await page.getByLabel('Token do proprietário',{exact:true}).fill('browser-test-owner-token-0000000000000000');
    await page.getByLabel('Manter acesso por 7 dias neste dispositivo').check();await click('Entrar no meu espaço');
    await page.getByRole('heading',{name:'O que vamos construir hoje?'}).waitFor();
    const cookie=(await context.cookies()).find(c=>c.name==='aurora_session');assert.ok(cookie.httpOnly);assert.equal(cookie.sameSite,'Strict');
    assert.equal(await page.evaluate(()=>Object.keys(localStorage).some(k=>/token|key|session/i.test(k))),false);
    for (const width of [1440, 1024, 768, 390, 320]) {
      await page.setViewportSize({width,height:900});
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
      assert.ok(await page.getByLabel('Sua mensagem',{exact:true}).isVisible());
    }
    await page.setViewportSize({width:1440,height:1000});
    await page.getByRole('button',{name:'Organizar uma ideia',exact:false}).click();
    assert.equal(await page.getByLabel('Sua mensagem',{exact:true}).inputValue(),'Ajude-me a organizar uma ideia. Comece perguntando o que pretendo desenvolver.');
    assert.equal(await page.getByLabel('Sua mensagem',{exact:true}).evaluate(el=>el===document.activeElement),true);
    if(process.env.AURORA_QA_DESKTOP) await page.screenshot({path:process.env.AURORA_QA_DESKTOP});
    await send('Projeto de teste sobre árvores');
    await click('Renomear');await page.getByLabel('Título da conversa',{exact:true}).fill('Meu projeto urbano');await click('Salvar título');
    await page.getByRole('button',{name:'Meu projeto urbano',exact:true}).waitFor();
    const textFile=await download('Exportar TXT','conversation.txt');assert.match(await fs.readFile(textFile,'utf8'),/árvores/);
    const jsonFile=await download('Exportar JSON','conversation.json');assert.equal(JSON.parse(await fs.readFile(jsonFile,'utf8')).messages.length,2);
    await page.getByLabel('Buscar conversas',{exact:true}).fill('ÁRVORES');await click('Buscar');await page.getByRole('button',{name:'Meu projeto urbano',exact:true}).waitFor();
    await page.getByLabel('Buscar conversas',{exact:true}).fill('nonexistent');await click('Buscar');await page.getByText('Nenhuma conversa encontrada.').waitFor();await click('Limpar busca');
    await page.reload();await page.getByRole('button',{name:'Meu projeto urbano',exact:true}).waitFor();assert.equal(await page.getByLabel('Token do proprietário',{exact:true}).count(),0);
    await click('Configurações');await page.getByLabel('Como você quer ser chamado?').fill('Willhas');
    await page.getByLabel('Estilo de resposta').selectOption('conciso');await page.getByLabel(/Outras preferências/).fill('Explique os termos com exemplos.');
    assert.ok(await page.getByRole('button',{name:'Salvar e usar preferências',exact:true}).isDisabled());
    await page.getByLabel('Autorizo salvar estas preferências e enviá-las ao provedor nas próximas mensagens.').check();await click('Salvar e usar preferências');
    await page.getByText('Preferências salvas. Serão usadas a partir da próxima mensagem.').waitFor();
    const preferenceFile=await download('Exportar preferências','preferences.json');assert.equal(JSON.parse(await fs.readFile(preferenceFile,'utf8')).name,'Willhas');
    await click('Administração');await waitEnabled('Baixar backup completo');
    const backupFile=await download('Baixar backup completo','backup.json');const backup=JSON.parse(await fs.readFile(backupFile,'utf8'));assert.equal(backup.conversations.length,1);assert.equal(backup.preferences.name,'Willhas');assert.equal(backup.sessions,undefined);
    await click('Conversar');await click('Nova conversa');await send('Conversa criada depois do backup');
    await click('Administração');await waitEnabled('Baixar backup completo');
    await page.getByLabel('Backup completo da Aurora 0.2 (.json)').setInputFiles({name:'invalid.json',mimeType:'application/json',buffer:Buffer.from('not JSON')});
    await page.getByRole('alert').filter({hasText:'Arquivo inválido'}).waitFor();
    await page.getByLabel('Backup completo da Aurora 0.2 (.json)').setInputFiles(backupFile);await page.getByRole('heading',{name:'Confira antes de restaurar'}).waitFor();
    assert.ok(await page.getByRole('button',{name:'Confirmar restauração',exact:true}).isDisabled());
    await page.getByLabel('Digite RESTAURAR para confirmar').fill('RESTAURAR');assert.ok(await page.getByRole('button',{name:'Confirmar restauração',exact:true}).isDisabled());
    await page.getByLabel('Autorizo restaurar estas preferências e usá-las nas próximas respostas.').check();await click('Confirmar restauração');
    await page.getByText('Backup restaurado. A cópia anterior está disponível abaixo.').waitFor();
    await waitEnabled('Baixar cópia');const recoveryFile=await download('Baixar cópia','recovery.json');assert.equal(JSON.parse(await fs.readFile(recoveryFile,'utf8')).conversations.length,2);
    await page.reload();await click('Configurações');await page.waitForFunction(()=>document.getElementById('pref-name')?.value==='Willhas');
    page.once('dialog',dialog=>dialog.accept());await click('Apagar preferências');await page.getByText('Preferências apagadas.').waitFor();
    await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:process.env.AURORA_QA_SCREENSHOT || path.join(directory,'mobile.png')});
    await click('Abrir histórico');
    const history=page.getByRole('complementary',{name:'Histórico de conversas'});
    await history.getByRole('button',{name:'Fechar histórico',exact:true}).focus();
    await page.keyboard.press('Shift+Tab');
    assert.equal(await page.evaluate(()=>document.getElementById('history-panel').contains(document.activeElement)),true);
    await page.keyboard.press('Escape');
    assert.equal(await page.getByRole('button',{name:'Abrir histórico',exact:true}).evaluate(el=>el===document.activeElement),true);
    await click('Abrir histórico');await page.getByRole('button',{name:'Meu projeto urbano',exact:true}).click();
    await page.getByText('RESPOSTA SIMULADA DE TESTE: Projeto de teste sobre árvores',{exact:true}).waitFor();
    await send('Mensagem do celular');
    await click('Alternar tema');assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
    if(process.env.AURORA_QA_LIGHT) await page.screenshot({path:process.env.AURORA_QA_LIGHT});
    await page.reload();assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
    await click('Abrir histórico');await page.getByRole('button',{name:'Excluir Meu projeto urbano',exact:true}).click();await click('Cancelar');
    await page.getByRole('button',{name:'Excluir Meu projeto urbano',exact:true}).click();await click('Excluir conversa');
    await page.getByRole('complementary',{name:'Histórico de conversas'}).getByRole('button',{name:'Fechar histórico',exact:true}).click();await click('Sair');await page.getByLabel('Token do proprietário',{exact:true}).waitFor();await page.reload();await page.getByLabel('Token do proprietário',{exact:true}).waitFor();
    assert.deepEqual(errors,[]);
    console.log('PASS: sessão e reload, busca/renomeação, exports TXT/JSON, consentimento e exclusão de preferências, backup/preview/restore/recovery, celular, tema, exclusão de conversa, logout; sem exceções JS. IA simulada apenas no servidor de testes.');
  } finally {await browser.close();await fs.rm(directory,{recursive:true,force:true});}
})().catch(error=>{console.error(error);process.exit(1);});
