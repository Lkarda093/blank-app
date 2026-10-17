# Aurora Desktop 0.7.0-desktop.2 — Correção 1

Esta prévia usa a interface Cosmic UI existente dentro de uma janela nativa para Windows. O chat, os temas, as cores e o layout principal foram preservados. A janela de configuração agora permite escolher Nuvem/Gemini, llama.cpp ou Ollama. Não é um instalador `.exe` independente: ainda requer Python e Node na instalação.

## O que mudou nesta entrega

- Nova configuração começa em **Nuvem/Gemini**, sem iniciar motor local. Configurações locais existentes continuam locais; não são convertidas automaticamente.
- A chave Gemini é cadastrada no **Gerenciador de Credenciais do Windows**, credencial genérica `Aurora/Gemini/APIKey`, restrita ao usuário atual neste computador. A aplicação lê a chave em memória para fazer requisições; não a devolve à interface, ao backup ou ao arquivo de configuração.
- Não há alternativa de salvar a chave em arquivo quando o cofre falha. Sem chave ou sem acesso ao cofre, o modo nuvem informa o problema e não troca para motor local.
- O modo local nunca troca para nuvem automaticamente e não acessa o cofre Gemini. Ollama marcado como remoto continua recusado.
- Ativar ou reconfigurar nuvem exige confirmar o aviso de privacidade. Serviços gratuitos Gemini podem usar mensagens e respostas para melhorar produtos, inclusive com revisão humana, conforme os termos aplicáveis. Projetos com faturamento têm condições diferentes e podem cobrar uso. A Aurora não consulta preços, saldo ou gratuidade e não ativa faturamento.
- O botão de remover chave atua apenas na credencial da Aurora e pede confirmação; preserva conversas e arquivos.
- O configurador web antigo deixou de escrever chave em `.env`. O carregador web recusa chave preenchida nesse arquivo. Windows usa o mesmo cofre; servidor não Windows pode receber segredo pelo ambiente, sem gravação feita pela Aurora.

Não foram removidas telas. Nenhuma tarefa, plugin, controle do PC ou serviço em segundo plano foi adicionado. A Correção 2 (Job Object, detecção de motor órfão e logs limitados) **ainda não foi implementada**; o risco de motor sobreviver ao encerramento forçado continua nesta prévia.

## Antes de atualizar

Estes são passos para o proprietário executar quando autorizar o teste; esta entrega não executou nada no PC.

1. Na Aurora anterior, exporte um backup em Configurações → Dados e guarde o JSON em uma pasta pessoal, fora do repositório. Ele pode conter conversas e documentos.
2. Feche a Aurora. Faça uma cópia da pasta `%LOCALAPPDATA%\Aurora`, se existir, enquanto ela estiver fechada. Essa cópia contém dados pessoais; não publique nem envie para uma IA.
3. Mantenha a pasta do programa anterior separada. O código anterior está preservado também na branch `backup/aurora-2026-10-17-antes-correcao-1`, commit `d9f70eecb912db605c792af2f3a4f0af7110d12d`. Esse backup de código não inclui seus dados nem credenciais.
4. Use uma pasta nova para a versão `0.7.0-desktop.2`. Não substitua seus dados pessoais pelo conteúdo do repositório.

## Preparar no Windows

1. Instale Python **3.12**, com Python Launcher: https://www.python.org/downloads/windows/ . Os arquivos Python 3.14 da raiz do repositório são remanescentes do modelo Streamlit, não instruções para o desktop.
2. Instale Node.js LTS **22.12 ou superior**: https://nodejs.org/ .
3. Confirme o WebView2 Runtime: https://developer.microsoft.com/microsoft-edge/webview2/ .
4. Na pasta `aurora-v0.1` que contém este documento, execute `Instalar-Aurora.cmd`. Isso baixa dependências e compila a interface. Se houver erro, não considere a instalação concluída.
5. Execute `Configurar-Aurora.cmd` para escolher um modo. Feche a Aurora antes de reconfigurar.
6. Depois de salvar, abra `Iniciar-Aurora.cmd`. Se não houver configuração anterior, ele abre a configuração primeiro.

Não há inicialização automática com o Windows. A execução desktop compilada não inicia Node/Vite. A API escuta somente em `127.0.0.1`; acesso pelo celular não está habilitado.

## Nuvem / Gemini — padrão de novas instalações

1. Escolha **Nuvem / Gemini**. Não é necessário baixar Ollama, llama.cpp ou um modelo GGUF.
2. Copie o identificador exato de um modelo de texto disponível no seu Google AI Studio. A Aurora não inventa identificadores nem verifica automaticamente se sua conta tem acesso.
3. Cole a chave no campo oculto da configuração. **Nunca envie a chave no chat, em captura de tela ou no GitHub.** Deixar o campo vazio mantém a chave já cadastrada no cofre; uma primeira configuração exige chave.
4. Leia o aviso de privacidade, confira as condições de custo do seu projeto e marque o aceite. Salvar a configuração não faz chamada ao Gemini.
5. Clique em Salvar configuração e abra a Aurora. Abrir a janela não envia pergunta ao Google nem inicia motor local.

Não há lista automática de modelos nesta janela: a configuração desta entrega usa um identificador informado pelo proprietário. O modelo aparece no seletor já existente do chat. Trocas automáticas entre modelos não são habilitadas nessa nova configuração desktop.

Os termos consultados em 17/10/2026 estão em https://ai.google.dev/gemini-api/terms . A condição da conta deve ser conferida no Google; a Aurora não consegue garantir que uma requisição será gratuita. Antes de um teste que possa gerar cobrança, é necessário definir o limite de gasto autorizado.

### Chave antiga em `.env`

O desktop não lê `backend/.env`. Para usar nuvem, cadastre a chave pelo configurador. No fluxo web, a versão atual recusa `GEMINI_API_KEY` preenchida em `.env` em vez de continuar com armazenamento em texto.

Nenhuma chave antiga é movida ou apagada automaticamente. Cadastre-a primeiro no cofre, remova a linha antiga do arquivo pessoal quando decidir fazer essa migração e não coloque esse arquivo nos backups de código. Se uma chave tiver sido publicada, excluí-la do arquivo não a torna segura: revogue-a no provedor e cadastre outra. Não é possível comprovar por esta entrega que cópias antigas deixaram de existir.

## llama.cpp — opcional

O pacote do motor e o modelo devem ser obtidos separadamente, de origem confiável. O programa escolhido será executado com os direitos do seu usuário, sem shell intermediário.

- Motor oficial: https://github.com/ggml-org/llama.cpp/releases . Para o primeiro teste, pacote Windows x64 CPU, mantendo as DLLs junto do executável.
- Escolha o executável `llama-server.exe` e um modelo GGUF de instruções na configuração. A RAM total do PC precisa ser conhecida antes de escolher o tamanho do modelo.
- O perfil atual usa CPU, dois threads, contexto de 4096 tokens, uma sequência e GPU desativada. As respostas locais são limitadas a 768 tokens e o contexto da requisição a 6000 caracteres.
- O motor começa ao abrir a Aurora e permanece carregado até o fechamento normal. Uma carga que ultrapassa dois minutos é interrompida.
- Fechamento forçado ainda pode deixar o motor aberto; essa proteção é o trabalho da Correção 2. Não use encerramento forçado como teste de aceitação desta entrega.

Não há download ou escolha automática de executável/modelo. Nenhum motor, DLL ou peso foi incluído no repositório.

## Ollama — opcional

Use apenas uma instalação e um modelo local que você já tenha preparado e autorizado. Selecione Ollama e informe seu identificador exato. A Aurora consulta `127.0.0.1:11434`; não instala, não inicia nem encerra o servidor externo Ollama. A requisição pede retenção do modelo por dois minutos; o próprio Ollama administra seus processos e sua distribuição CPU/GPU.

Falha de conexão, modelo ausente ou modelo remoto resultam em erro local. Não há troca automática para Gemini.

## Dados e credenciais

- `%LOCALAPPDATA%\Aurora\aurora.sqlite3`: banco existente; conversas, documentos, perfis, projetos, memórias e resumos. O banco não ganhou migração nesta entrega e não foi criptografado por ela.
- Arquivos auxiliares `-wal` e `-shm` podem ser criados pelo SQLite.
- `%LOCALAPPDATA%\Aurora\desktop.json`: somente configuração não secreta; modo, modelo ou caminhos locais. A gravação temporária também não recebe a chave.
- `%LOCALAPPDATA%\Aurora\desktop.lock`: trava de instância.
- `%LOCALAPPDATA%\Aurora\webview`: perfil persistente da janela, incluindo preferências e rascunhos de mensagens.
- `backups`, ao lado do banco: cópias de recuperação de migrações/restaurações já existentes.
- Downloads TXT/JSON e backups exportados ficam no destino escolhido pelo navegador/WebView2.
- A chave é administrada pelo cofre do Windows, fora do projeto e dos backups da Aurora. Outros programas executados como o mesmo usuário não são isolados por uma conta de sistema separada.

No modo local a Aurora continua sem enviar requisições de inferência para a nuvem. Isso não constitui garantia sobre tráfego próprio do Windows, WebView2 ou de programas externos instalados.

## Validação desta entrega

Antes: **158 testes Python e 10 testes JavaScript passaram**. Depois: **175 testes Python e 10 testes JavaScript passaram**, além da compilação de produção. O aviso de depreciação Starlette/TestClient já existia; não houve falha nesses testes.

Os novos testes cobrem: persistência da credencial pelo contrato nativo simulado, falha do cofre, dados corrompidos, remoção, ausência de segredo na configuração e nas representações de Settings, bloqueio de chave em `.env`, cancelamento da configuração, aceite de privacidade, isolamento do modo local e inicialização HTTP do modo nuvem sem criar/consultar motor local. A janela e o cofre são simulados. Não foram feitas chamadas reais ao Gemini ou a modelos locais.

Medição comparável em processos novos no Linux, API exercitada por TestClient, intervalo ocioso de três segundos, **sem WebView2, sem motor e sem inferência**:

| Provedor configurado | Pico de RAM do processo antes | Depois | CPU ociosa antes → depois, um núcleo |
|---|---:|---:|---:|
| Gemini | 46,36 MiB | 45,46 MiB | 0,002% → 0,001% |
| llama.cpp, sem motor | 46,08 MiB | 46,35 MiB | 0,002% → 0,002% |

Esses números são de pico de RAM do processo de teste, não de RAM total em repouso do desktop. São uma amostra curta sujeita a variação e não demonstram ganho de desempenho. O Windows real, WebView2, diálogos nativos, gravação real no cofre e o PC do proprietário ainda não foram testados. `App.jsx` e `style.css` permaneceram idênticos à linha de base; a única alteração na interface React foi a orientação textual de credenciais em Configurações.

## Teste de aceitação no Windows — após autorização

1. Com a Aurora fechada, abra o Gerenciador de Tarefas (`Ctrl+Shift+Esc`). Registre RAM disponível e quais motores locais já estavam abertos; não encerre outros programas por suposição.
2. Configure Nuvem/Gemini e salve. Confira em Painel de Controle → Gerenciador de Credenciais → Credenciais do Windows se existe a credencial genérica `Aurora/Gemini/APIKey`. Não revele seu conteúdo.
3. Abra a Aurora sem enviar mensagem. Confira que ela não abriu um novo `llama-server.exe` ou Ollama. Registre a memória e CPU da árvore de processos Python/WebView2, evitando contar apenas um processo.
4. Feche e reabra; confira histórico e preferências. Teste exportação TXT/JSON e backup com dados de teste, sem compartilhar o conteúdo pessoal.
5. O envio de uma pergunta Gemini fica para depois de confirmar conta/cotas e orçamento. Nenhum teste automatizado desta entrega confirma a elegibilidade gratuita do seu projeto.
6. Se desejar testar um modo local, prepare e autorize o motor separadamente. Verifique erro local quando ele está indisponível, sem troca para Gemini. Registre memória antes/depois; os 4 GB da GTX são VRAM, não a RAM total do computador.
7. Anote o erro exato sem incluir chave, token, conversa privada ou arquivo pessoal. Não considere esta prévia validada no Windows apenas porque os testes simulados passaram.

## Arquivos desta entrega

- `desktop/launcher.py`: seleção dos modos, configuração não secreta e criação de Settings a partir do cofre.
- `backend/app/credentials.py` e `backend/app/cloud_policy.py`: cofre Win32 e aviso compartilhado.
- `backend/app/config.py`, `backend/.env.example`, `scripts/configure.py` e `scripts/list_models.py`: eliminar orientação/uso de chave em arquivo no fluxo atualizado.
- `backend/app/conversations/routes.py` e `backend/app/main.py`: aviso e identificação de versão.
- `frontend/src/SettingsPanel.jsx`: apenas orientação textual sobre configuração e credenciais.
- `frontend/package.json` e `frontend/package-lock.json`: versão desktop.2; dependências de execução mantidas.
- `backend/tests/test_desktop_cloud.py` e `backend/tests/test_config.py`: contratos novos e ajuste da configuração segura.
- `DESKTOP.md`, `README.md`, `DECISOES.md` e `CONTEXTO_PARA_IA.md`: guia atual, decisões, limites e continuidade.

## Como reverter

Feche a Aurora. Volte à pasta anterior ou à branch de backup mencionada acima. O esquema do banco não foi alterado, mas preserve a cópia pessoal feita antes da atualização. Restaure a configuração anterior, se necessário. Voltar o código não apaga a credencial do cofre: ela pode ser removida pelo configurador novo ou manualmente pelo Gerenciador de Credenciais, com sua autorização. O código antigo não oferece Gemini no desktop e pode voltar a aceitar chave em `.env`; não restaure uma chave em texto para contornar essa limitação.

## Próximos trabalhos

Correção 2: Job Object do Windows, verificação de motor órfão da própria Aurora e logs limitados sem prompts. Lista de espera, uma autorização por vez: tarefas/cronogramas, formatação, consolidação da documentação, sobras Streamlit e acesso pelo celular. Voz, mascote, controle remoto, Android nativo, OpenClaw, fusão Jarvis e plugins de AutoCAD/Revit permanecem fora do escopo.

Referência técnica do cofre: https://learn.microsoft.com/en-us/windows/win32/api/wincred/ns-wincred-credentialw , CredReadW e CredWriteW. A implementação usa somente a biblioteca padrão Python/Win32, sem novo serviço ou dependência de execução.
