# Validação — Aurora 0.3.2

Execução concluída em 12/10/2026. Linux, Python 3.12.14 e Node 24.19.0. Versões instaladas fixadas nos requisitos e package-lock.

| Verificação | Resultado |
| --- | --- |
| Testes Python completos | 79 passaram com troca automática por cota |
| Cliente JavaScript | 6 passaram |
| Compilação Python e sintaxe Bash | Passaram |
| Build React/Vite/Tailwind | Concluído |
| Teste Chromium em desktop 1440×1000 | Passou |
| Teste Chromium móvel 390×844 | Passou, com inspeção visual |
| Migração de SQLite schema 1 para 2 | Testada com dados existentes e cópia anterior preservada |
| Sessão após reinício da API | Testada com SQLite persistente |
| Chamada real Gemini da 0.1 | Confirmada pelo proprietário nesta conversa, usando gemini-3.8-flash |
| Personalização real Gemini da 0.2 com a conta do proprietário | Pendente após atualizar o Codespace; não temos acesso à chave |
| Instalação da 0.2 no Codespace do proprietário | Confirmada pelo proprietário: busca, renomeação, exports, download de backup, preferências após reload e prévia de restauração |
| Instalação da 0.3 no Codespace do proprietário | Pendente após atualizar |
| Layout em 320, 390, 768, 1024 e 1440 pixels | Sem rolagem horizontal; campo de mensagem visível |
| Histórico móvel por teclado | Foco contido, Escape fecha e retorna ao botão de abertura |
| Temas claro/escuro | Inspecionados visualmente; preferência preservada após reload |

## Correção Aurora Cosmic UI 0.3.1

Objetivo: seguir a composição de `01_inicio_pc(1).png`, `07_tema_claro_responsivo(1).png`, demais telas conceituais e o texto fornecido pelo proprietário. Critérios: lateral esquerda única por padrão, saudação à esquerda, seis cartões, provedores, compositor compacto, cinco ações rápidas, paisagem, módulos independentes com estado honesto e Configurações centralizadas. Implementados e inspecionados no Chromium.

A paisagem é uma recriação vetorial decorativa, não o mesmo arquivo raster da referência. Gemini continua sendo o único provedor real. Biblioteca não contém pastas/arquivos fictícios; ferramentas e computador não executam ações.

A verificação no navegador adicional cobriu: saudação atualizada pelo nome consentido; tema automático seguindo mudanças do sistema e reload; troca de cores e efeitos; histórico à esquerda/direita sem duplicar pesquisa, recolhimento e expansão; fixação local; grade de agentes com seleção Gemini; busca nas ferramentas; controles indisponíveis da biblioteca; aviso do computador; ações rápidas preenchendo texto sem enviar; avisos dos recursos em desenvolvimento; menu móvel com foco contido, Escape e retorno ao botão. Os fluxos de backup e preferências anteriores foram executados na nova organização em abas.

As dependências de produção e o schema SQLite 2 foram mantidos. O número público da aplicação passou a 0.3.1; o formato do backup não mudou. As escolhas visuais, posição do histórico, fixações e modelo preferido são preferências deste navegador; não fazem parte do backup do servidor. Preferências pessoais autorizadas continuam em SQLite.

## Cobertura

Os testes anteriores de chat, autenticação, falhas do Gemini, persistência, confirmação/cascata de exclusão, idempotência, paginação e configuração continuam na suíte.

Novos testes cobrem:

- Renomeação, limites, busca Unicode literal, caracteres SQL tratados como texto e exportação completa além da página carregada.
- Consentimento obrigatório, atualização/exclusão de preferências e personalização enviada ao adaptador e no corpo HTTP do Gemini.
- Snapshot sem credenciais ou sessões, prévia, confirmação, assinatura do arquivo, revisão, consentimento e restauração com cópia anterior recuperável.
- Arquivos de schema errado, campos desconhecidos, relações órfãs, identificadores duplicados, datas inválidas, JSON malformado e limites de tamanho.
- Mudança nos dados após a prévia; restauração durante geração; rollback diante de falha SQL e falha ao criar a cópia anterior.
- Rotas de dados inacessíveis sem autenticação; sessão HttpOnly, SameSite e Secure; cabeçalho/Origin em escritas; logout, expiração, rotação do token e limitação de tentativas de login.
- Migração real de um banco com schema 1, preservação do par de mensagens e cópia SQLite anterior; reinício com schema 2 não repete a cópia.

A suíte Python emite um aviso de depreciação do TestClient Starlette sobre HTTPX; nenhum teste falhou.

## O que foi real no teste de navegador

Frontend React, Vite, proxy, API FastAPI, cookies, SQLite, downloads, uploads e restauração foram reais. Somente a IA foi substituída pelo servidor exclusivamente de testes `backend/tests/e2e_server.py`, com mensagens iniciadas por **RESPOSTA SIMULADA DE TESTE**. O comando normal `start.sh` usa `app.main:app` e o Gemini real.

O fluxo validou: rejeição de token incorreto, entrada lembrada, reload sem nova senha, ausência de token em localStorage, envio, renomeação, busca por mensagem, exportações TXT/JSON, consentimento/salvamento/exportação/exclusão de preferências, backup completo, recusa de JSON inválido, prévia e confirmação com consentimento, restauração removendo conversa posterior ao backup, download da cópia anterior com os dados removidos, persistência de preferências após reload, painel móvel, envio móvel, tema, confirmação/cancelamento de exclusão, logout e novo reload sem sessão. Não houve exceções JavaScript no fluxo completo.

## Reproduzir verificações básicas

Na raiz do projeto, com .venv ativada:

```bash
python -m pip install -r backend/requirements-dev.txt
python -m compileall -q backend/app scripts
bash -n scripts/start.sh
cd backend
python -m pytest -q
cd ..
npm --prefix frontend test
npm --prefix frontend run build
```

## Teste de navegador opcional

Não é necessário baixar Playwright para usar a assistente. Para QA, pare a aplicação normal e instale temporariamente:

```bash
cd frontend
npm install --no-save --package-lock=false playwright
npx playwright install chromium
cd ..
python scripts/browser_test.py
```

O harness inicia a API de testes e o Vite, cria um SQLite temporário e encerra os processos/removes os dados ao terminar. As portas 8000 e 5173 devem estar livres. `npm --prefix frontend ci` remove as dependências temporárias e repõe exatamente as normais.

Nesta execução foi usado um Chromium alternativo de QA já disponível no ambiente, selecionado por `AURORA_TEST_CHROMIUM`, devido à falha anterior do download padrão. O navegador de QA não é incluído no projeto ou nas dependências de produção. Screenshots serviram somente à inspeção interna.

## Limites da verificação

Não foi realizado benchmark de RAM/carga, teste em Android físico, Safari, Firefox ou Windows nativo. Build: aproximadamente 253 kB JS principal (80 kB gzip), 24 kB JS adicional de módulos sob demanda (7,4 kB gzip) e 36 kB CSS (8 kB gzip), sem modelos locais ou fontes externas. A suíte não faz chamadas pagas ao Google. Confirmar a interface Cosmic UI 0.3.1 com Gemini real depende de atualizar o Codespace do proprietário. O adaptador Gemini não foi alterado nesta versão. Não foi realizada auditoria completa de acessibilidade ou teste com leitor de tela.

## Falhas intermitentes Gemini

Oito casos adicionais testaram recuperação após 500/503 com corpo de mensagem preservado, espera exponencial limitada, encerramento após três falhas, código HTTP sem conteúdo privado, ausência de repetição após sucesso/cota/modelo/timeouts/conexão e cancelamento real por deadline. Total: 65 testes Python passaram. O transporte HTTP foi simulado; não foi usada a chave do proprietário nem se comprovou a causa específica do erro relatado. As verificações anteriores de frontend permanecem aplicáveis porque esta correção não altera a interface.

## Troca automática por cota

14 novos casos do backend cobrem configuração explícita da lista, seleção de alternativas apenas após 429, limitação a três modelos, falhas sem gravação parcial, ausência de troca por outros erros, toggle desligado e compatibilidade de clientes anteriores, modelo efetivo no SQLite/backup, reenvio idempotente após troca e reinício, conflito de payload, deadline geral com liberação da trava e exclusão em cascata dos metadados auxiliares. Total: 79 testes Python.

O fluxo Chromium também verifica aviso de troca, seletor atualizado, modelo efetivo visível após reload, opção desligada impedindo troca e reativação salvando apenas um novo par de mensagens. O backend de QA simula cota em test-model e sucesso em test-alternate; nenhum modelo real ou custo foi usado. A chamada real e a elegibilidade gratuita precisam ser conferidas no projeto do proprietário.
