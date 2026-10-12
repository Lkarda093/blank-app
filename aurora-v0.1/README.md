# Aurora 0.3 — assistente pessoal

Uma base pequena para sua assistente: React + Vite + Tailwind CSS, FastAPI, Gemini e histórico SQLite. Interface em português, clara/escura, responsiva, com histórico à direita. Esta é uma nova implementação; não modifica nem migra automaticamente projetos Streamlit ou o pacote Aurora anterior.

**Já usa a 0.2? Comece por [Atualizar para 0.3](docs/ATUALIZAR_0.3.md).** Se ainda usa a 0.1, veja também [a migração para 0.2](docs/ATUALIZAR_0.2.md). Para uma instalação nova, siga a seção 2. A pasta e branch continuam chamadas `aurora-v0.1` para facilitar a atualização. Nenhuma versão seguinte será implementada sem sua autorização.

## 1. O que está implementado

Novidades da 0.3: identidade violeta/azul, navegação com nomes visíveis, barra inferior móvel, histórico com foco de teclado e exportações identificadas. Não altera o esquema do banco nem adiciona dependências.

Recursos mantidos da 0.2: busca e renomeação de conversas; exportação em TXT/JSON; backup completo JSON; restauração com prévia, confirmação e cópia de recuperação; preferências editáveis e consentidas; sessão no navegador com opção de 7 dias. Migração automática do SQLite preserva o histórico da 0.1 e gera uma cópia anterior à atualização.

- Frontend React funcional, envio de texto e exibição das respostas.
- Adaptador real para a API REST Gemini `generateContent` por HTTPS; sem respostas fictícias no aplicativo normal.
- Histórico por conversa, salvo em SQLite; criação e exclusão com confirmação.
- Autenticação do proprietário por token na entrada e sessão HttpOnly no navegador. Bearer continua disponível para clientes da API.
- Seleção entre os modelos explicitamente autorizados em `GEMINI_MODELS`.
- Tema persistido no navegador. A chave da API nunca é enviada ao navegador.
- Configurações com preferências e status real de conexão; painel administrativo com estatísticas, backup e restauração.
- Erros para configuração ausente, cota, permissão, modelo indisponível, conexão, timeout e resposta bloqueada.
- Contexto limitado, paginação do histórico e proteção contra duplicação de envios concluídos.

**Não implementado:** voz, anexos, imagens/vídeos, pesquisa web, biblioteca, Obsidian, plugins, usuários adicionais, agente local e outros provedores. Expansões ficam descritas no painel administrativo como planejamento. As respostas são texto simples; Markdown e código aparecem como texto, sem execução ou HTML.

## 2. Primeiro uso no GitHub Codespaces

Você precisa de uma conta GitHub, um Codespace com Python 3.12 e Node 22.12+ e uma chave da API Gemini. Codespaces e Gemini têm condições/cotas próprias; não há garantia de gratuidade.

### 2.1 Coloque o projeto no Codespace

1. Baixe e extraia o ZIP.
2. Crie um repositório privado no GitHub e um Codespace para ele, ou abra seu Codespace atual.
3. Pelo explorador de arquivos do VS Code, envie a pasta extraída `aurora-v0.1` ao Codespace. Se enviar o ZIP, extraia pelo terminal com `unzip NOME_DO_ARQUIVO.zip`.
4. No terminal, entre na pasta que contém este README:

```bash
cd aurora-v0.1
```

Se você colocou **o conteúdo** da pasta diretamente na raiz do repositório, pule esse `cd`. O terminal deve estar na pasta que contém `backend`, `frontend` e `scripts`.

O arquivo `.devcontainer/devcontainer.json` oferece Python 3.12, Node 22 e encaminhamento da porta 5173. Para o GitHub aplicá-lo, ele precisa estar na **raiz do repositório**, e você deve reconstruir o contêiner. Ele não altera o ambiente de um Codespace existente quando está dentro de uma subpasta. Você também pode usar o ambiente existente se as versões abaixo forem adequadas.

```bash
python --version
node --version
```

### 2.2 Instale as dependências uma vez

Execute na pasta do projeto:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
```

A instalação usa a internet. O `package-lock.json` e os arquivos de requisitos fixam as versões testadas. `node_modules`, `.venv` e os modelos de IA não são incluídos no ZIP. Nenhum modelo pesado é baixado.

### 2.3 Configure a chave e o acesso

Crie uma chave em https://aistudio.google.com/apikey. Consulte o modelo de **texto** disponível para seu projeto no AI Studio e suas condições de uso. Não confunda assinatura do aplicativo Gemini com acesso à API.

```bash
python scripts/configure.py
```

O programa pede a chave (a digitação fica oculta) e o identificador do modelo. Ele cria `backend/.env` com um token forte de proprietário. Você pode deixar chave e modelo vazios para apenas examinar a interface; o envio ficará desativado. Nenhum modelo é selecionado automaticamente porque disponibilidade, cotas e preços variam.

Para encontrar os identificadores de modelos que sua chave anuncia como compatíveis com `generateContent`, depois de configurar a chave execute:

```bash
python scripts/list_models.py
```

Essa consulta usa sua chave no servidor e não gera texto. A listagem não comprova que você tem cota de geração ou gratuidade. Copie um identificador de modelo adequado a chat de texto para `GEMINI_MODELS` no arquivo `backend/.env`. Não escolha modelos de imagem, voz ou embedding. Você pode informar mais de um modelo de texto, separado por vírgula; apenas esses modelos aparecerão na interface.

Alternativa manual: copie `backend/.env.example` para `backend/.env`, preencha os campos no editor e gere o token com `python -c 'import secrets; print(secrets.token_urlsafe(32))'`. Use pelo menos 32 caracteres aleatórios. Não coloque a chave em variável `VITE_*`, código React, URL ou chat. Nunca envie `.env` para o GitHub.

### 2.4 Inicie tudo

```bash
bash scripts/start.sh
```

1. Abra a aba **Ports/Portas** do Codespaces.
2. Localize a porta **5173**, mantenha a visibilidade **Private/Privada** e clique em **Open in Browser/Abrir no navegador**.
3. Abra `backend/.env` no editor e copie somente o valor de `AURORA_OWNER_TOKEN` para a tela de entrada. Não use a chave Gemini como token.
4. Clique em **Nova conversa**, escolha o modelo e envie uma mensagem.

O script inicia o backend em `127.0.0.1:8000` e o frontend na porta 5173. O navegador acessa `/api` pela mesma origem, e o Vite encaminha ao FastAPI. Não é necessário tornar a porta 8000 pública. `Ctrl+C` encerra ambos. Mudanças em `.env` exigem reiniciar o backend; depois clique em Atualizar status nas configurações ou recarregue a página.

No computador local Linux/macOS, os mesmos comandos funcionam. Abra http://localhost:5173. No Windows, utilize WSL para esses comandos Bash. O acesso pelo celular nesta versão é pelo endereço HTTPS privado do Codespace, com autenticação no GitHub e token Aurora. O computador local não é exposto automaticamente.

**Sessão no navegador:** o token digitado não é salvo em localStorage. O servidor emite um cookie HttpOnly e SameSite=Strict. Em HTTPS, o cookie também é Secure. Sem a opção de lembrar, a sessão dura no máximo 12 horas; com a opção, até 7 dias. Recarregar não exige outro login. Use Sair para revogar a sessão deste navegador. Só o tema é salvo em localStorage.

### Alternativa: dois terminais

Primeiro terminal, na raiz do projeto:

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Segundo terminal, na raiz do projeto, para Codespaces:

```bash
npm --prefix frontend run dev -- --host 0.0.0.0
```

Para uso local, omita `-- --host 0.0.0.0`. Não use vários workers: a versão 0.2 permite apenas uma geração por vez por instância.

## 3. Como verificar o funcionamento

1. Sem chave/modelo: a interface entra, mas avisa sobre configuração incompleta e desabilita enviar.
2. Com chave/modelo válidos: envie “Responda apenas: Olá”. Deve surgir a resposta real do Google.
3. Envie uma segunda mensagem sobre a primeira. O contexto anterior será enviado junto.
4. Recarregue a página: a sessão deve continuar ativa. Abra a conversa no histórico.
5. Pare e reinicie a aplicação. O histórico deverá continuar no banco.
6. Alterne o tema e recarregue: o tema deve persistir.
7. Exclua uma conversa: primeiro cancele; depois confirme e verifique o desaparecimento.
8. Faça logout: a lista e o conteúdo são removidos da tela e a sessão é revogada.
9. Renomeie e busque uma conversa; exporte-a em TXT e JSON.
10. Salve preferências com consentimento, edite e apague-as.
11. Baixe um backup completo. Teste a restauração somente com dados de teste ou após preservar uma cópia importante; confira a prévia e a cópia de recuperação.

O Google recebe as preferências autorizadas (quando salvas), a mensagem atual e até 10 pares anteriores da mesma conversa, com limite de 40.000 caracteres no contexto. Conversas diferentes não compartilham contexto. O banco mantém o histórico completo. Máximo de 8.000 caracteres por mensagem e 4.096 tokens de saída solicitados. Uma resposta que atinge esse limite recebe um aviso.

Em erro de geração, nenhuma troca parcial é gravada e o texto permanece no campo. Ao reenviar sem alterar texto/modelo/conversa, o navegador reutiliza o identificador: se a troca já foi salva, ela é devolvida sem nova geração. Recarregar a página perde o rascunho e esse identificador; confira o histórico antes de reenviar. Timeout ou queda entre o processamento no Google e a gravação local pode consumir cota mesmo sem resposta salva. Não há repetição automática de chamadas pagas. Preferências autorizadas, quando salvas, são enviadas como personalização adicional ao provedor.

## 4. Testes e compilação

Na raiz do projeto, com o ambiente virtual ativo:

```bash
python -m pip install -r backend/requirements-dev.txt
python -m compileall -q backend/app scripts
cd backend
python -m pytest -q
cd ..
npm --prefix frontend test
npm --prefix frontend run build
```

Os testes Python usam SQLite temporário, um provedor de teste para o fluxo da API e HTTP simulado para verificar o adaptador real. Eles não precisam de chave, não chamam o Google e não consomem cota. Os testes JavaScript validam o cliente HTTP e suas falhas. A compilação gera `frontend/dist`; não instala um serviço de produção.

Consulte `docs/VALIDACAO.md` para os resultados realmente executados nesta entrega e as verificações pendentes. `backend/tests/e2e_server.py` é exclusivamente um servidor de testes com respostas explicitamente simuladas. O comando normal de inicialização nunca o carrega.

## 5. Estrutura

```text
aurora-v0.1/
├── README.md
├── .gitignore
├── .devcontainer/devcontainer.json
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pytest.ini
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── auth/{dependencies.py,routes.py}
│   │   ├── memory/routes.py
│   │   ├── data/routes.py
│   │   ├── conversations/routes.py
│   │   └── providers/{base.py,gemini.py}
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/{App.jsx,Preferences.jsx,DataPanel.jsx,main.jsx,style.css,api.js,api.test.js}
├── scripts/{configure.py,list_models.py,start.sh,browser_test.py}
└── docs/{ARQUITETURA.md,VALIDACAO.md,ATUALIZAR_0.2.md}
```

`backend/data/aurora.sqlite3` é criado na primeira execução. Os arquivos SQLite `-wal` e `-shm` podem existir enquanto o servidor está ativo. Nenhum dado pessoal ou segredo é incluído no pacote.

## 6. API documentada

Local: http://localhost:8000/docs. No Codespaces, se precisar de Swagger, encaminhe temporariamente a porta 8000 como **privada**. Clique em **Authorize** e informe o token do proprietário. O esquema de documentação e a verificação de saúde são públicos; não incluem segredos nem dados pessoais.

| Método | Caminho | Finalidade |
| --- | --- | --- |
| GET | `/api/health` | Processo disponível; não testa Gemini |
| GET | `/api/config` | Configuração sem segredos |
| GET | `/api/conversations?offset=0&limit=100` | Histórico paginado |
| POST | `/api/conversations` | Nova conversa |
| GET | `/api/conversations/{id}` | Últimos 50 pares e cursor `next_before` |
| GET | `/api/conversations/{id}?before=N` | Pares mais antigos |
| POST | `/api/conversations/{id}/messages` | Enviar `content`, `model`, `request_id` UUID |
| DELETE | `/api/conversations/{id}?confirm=true` | Excluir conversa e mensagens |

Todas as rotas de dados exigem bearer ou uma sessão válida. Escritas por cookie e entrada/saída precisam do cabeçalho `X-Aurora-Request: 1`; se houver Origin, ele precisa corresponder ao Host. A interface envia esses dados automaticamente. Segredos não são retornados. Erros incluem `detail` em português. Não há CORS aberto, execução de comandos ou acesso a caminhos enviados pelo navegador. Upload de backup recebe apenas JSON validado, nunca SQL executável.

## 7. Backup e recuperação manual

A versão 0.2 oferece backup/restauração pelo painel administrativo: consulte [as instruções](docs/ATUALIZAR_0.2.md). Para uma cópia SQLite manual e consistente, **pare o servidor primeiro** com Ctrl+C, na raiz do projeto:

```bash
mkdir -p backups
cp backend/data/aurora.sqlite3 "backups/aurora-$(date +%Y%m%d-%H%M%S).sqlite3"
```

Baixe esse arquivo para um local protegido fora do Codespace. Se você customizou `AURORA_DB_PATH`, use esse caminho. Nunca copie somente o `.sqlite3` enquanto o servidor estiver ativo, pois dados recentes podem estar no WAL. Não apague o Codespace sem baixar o backup.

Para restaurar: pare a aplicação, faça uma cópia da pasta de dados atual, mova a pasta de dados atual para um local de segurança e coloque o backup como `backend/data/aurora.sqlite3` em uma pasta de dados nova. Não misture o backup com antigos arquivos `-wal`/`-shm`. Inicie a aplicação e confira o histórico. Não faça uma restauração em cima de dados importantes sem preservar a cópia anterior.

`.env` não é incluído no backup do histórico: guarde as credenciais separadamente em um gerenciador de senhas ou reconfigure-as. A exclusão remove dados do banco ativo, mas não apaga cópias já feitas, resíduos forenses do disco nem eventuais registros do provedor.

## 8. Segurança e limites

Uso pessoal de desenvolvimento: um proprietário e um processo FastAPI. O token e a sessão concedem acesso a todos os dados; proteja o acesso ao navegador e à conta. Para revogar, gere outro token, altere `.env` e reinicie. Autenticação multiusuário, proteção contra força bruta distribuída e publicação de produção não fazem parte desta entrega. Sair revoga a sessão atual; trocar o token revoga todas após reinício. O login aplica uma limitação básica em memória. Mantenha as portas privadas.

O arquivo `.env` e o SQLite são protegidos por permissões de arquivo no Linux, mas **não são criptografados pelo aplicativo**. Qualquer pessoa com acesso à sua conta/Codespace/disco pode lê-los. Não cole dados sensíveis sem avaliar as condições do provedor. O aplicativo não mede seu saldo, não bloqueia gastos no Google e não torna APIs pagas gratuitas.

O aplicativo normal não registra o conteúdo dos prompts nem corpos brutos de erro do Google. Erros inesperados registram apenas o tipo da exceção. Logs de acesso do servidor ainda podem conter caminhos e identificadores de conversas. Nenhum log persistente de melhorias é implementado nesta versão.

Não há ferramentas oferecidas ao modelo. Pedidos do modelo não podem modificar arquivos, executar comandos, instalar plugins ou alterar código.

## 9. Problemas comuns

| Sintoma | O que fazer |
| --- | --- |
| Configuração incompleta | Preencha chave/modelos em backend/.env, reinicie e atualize o status |
| Token ausente/inválido | Copie AURORA_OWNER_TOKEN; não copie GEMINI_API_KEY |
| 429 / cota | Confira limites no AI Studio, espere e reenvie conscientemente |
| Modelo não encontrado | Consulte os modelos da conta e atualize GEMINI_MODELS |
| Conexão com servidor falhou | Confira os dois processos, a porta 5173 e os terminais |
| Porta ocupada | Encerre a instância anterior com Ctrl+C; não abra múltiplas cópias |
| Host bloqueado pelo Vite | Inicie dentro do Codespace; o Vite utiliza CODESPACE_NAME e GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN. Não use allowedHosts: true |
| Erro ao instalar Python | Confira Python 3.12 e ative a .venv |
| Frontend não compila | Confira Node 22.12+ e execute npm ci dentro de frontend |
| Preciso mudar .env | Pare com Ctrl+C, edite e inicie novamente |

## 10. Referências oficiais

- API Gemini e autenticação: https://ai.google.dev/api
- Contrato generateContent: https://ai.google.dev/api/generate-content
- Lista de modelos: https://ai.google.dev/api/models
- Preços e condições: https://ai.google.dev/gemini-api/docs/pricing
- Vite: https://vite.dev/guide/
- Tailwind com Vite: https://tailwindcss.com/docs/installation/using-vite

As condições do provedor podem mudar. Esta base não promete disponibilidade de um modelo específico nem funcionamento remoto sem configuração e teste com sua conta.

## 11. API da versão 0.2

| Método | Caminho | Finalidade |
| --- | --- | --- |
| POST | `/api/auth/login` | Token e opção remember; cria cookie |
| GET | `/api/auth/session` | Verifica sessão |
| POST | `/api/auth/logout` | Revoga sessão e apaga cookie |
| GET | `/api/conversations?q=texto` | Busca título ou mensagens |
| PATCH | `/api/conversations/{id}` | Renomeia com `title` |
| GET | `/api/conversations/{id}/export?format=txt` | Exporta todas as mensagens; aceita também json |
| GET / PUT / DELETE | `/api/preferences` | Consulta/salva/apaga preferências; PUT precisa `consent: true`, DELETE `?confirm=true` |
| GET | `/api/data/stats` | Contagens e revisão |
| GET | `/api/data/backup` | Download do backup completo |
| POST | `/api/data/restore/preview` | Recebe JSON completo e retorna resumo, revisão e ticket |
| POST | `/api/data/restore` | Mesmo JSON, com cabeçalhos de confirmação, revisão e ticket |
| GET | `/api/data/recovery` | Lista cópias anteriores às restaurações |
| GET | `/api/data/recovery/{id}` | Download da cópia de recuperação |

Restauração: `X-Aurora-Confirm: RESTAURAR`, `X-Aurora-Revision: REVISAO` e `X-Aurora-Preview: TICKET` retornados pela prévia; se houver preferências, `X-Aurora-Preferences-Consent: 1`. O ticket vincula o arquivo conferido à revisão atual. Arquivo alterado, dados modificados ou confirmação ausente impedem a substituição. A interface cuida de tudo isso.

Testes opcionais de navegador: instale temporariamente Playwright no frontend conforme docs/VALIDACAO.md e execute `python scripts/browser_test.py` com as portas livres e a venv ativada. O harness cria banco temporário e usa exclusivamente o provedor explicitamente simulado de testes.
