# Validação executada — versão 0.1

Data: 11/10/2026. Ambiente Linux, Python 3.12.14, Node 24.19.0. Dependências efetivamente instaladas estão fixadas nos arquivos de requisitos e package-lock.json.

| Verificação | Resultado |
| --- | --- |
| Compilação Python (`compileall`) | Passou |
| Sintaxe Bash (`bash -n scripts/start.sh`) | Passou |
| Backend (`pytest -q`) | 30 testes passaram |
| Cliente JavaScript (`npm test`) | 5 testes passaram |
| Frontend (`npm run build`) | Compilação concluída |
| Dependências de produção JS (`npm audit --omit=dev --audit-level=high`) | 0 vulnerabilidades reportadas naquele momento; não equivale a auditoria de segurança completa |
| Inicialização pelo `scripts/start.sh` | FastAPI e Vite iniciaram; proxy `/api`, SQLite e autenticação responderam |
| Configuração sem chave Gemini | Envio recusado corretamente com 503, sem chamada externa |
| Navegador Chromium, desktop 1440×1000 | Fluxos descritos abaixo passaram; inspeção visual realizada |
| Navegador Chromium, móvel 390×844 | Painel móvel e envio passaram, sem overflow horizontal; inspeção visual realizada |
| Chamada real ao Google com credenciais do proprietário | **Não executada: não foi fornecida uma chave** |
| Codespace real da conta do proprietário | **Não executado**; configuração e instruções fornecidas |
| Safari, Firefox, Android físico, Windows nativo | **Não executados** |

## Cobertura backend

Autenticação e omissão de segredos; criação; histórico; persistência ao recriar o aplicativo usando o mesmo arquivo; exclusão com confirmação e cascata; request_id idempotente e colisão; rejeição de mensagem vazia/extensa; modelo não autorizado; conversa inexistente; falha sem gravação parcial; reenvio após falha; contexto limitado com histórico preservado; paginação; bloqueio de envio/exclusão concorrentes.

O adaptador Gemini foi exercitado com transporte HTTP controlado: endpoint e cabeçalho corretos, roles user/model, filtragem de partes de pensamento, 400/401/403/404/429/500/503, ausência de texto, bloqueio, resposta malformada, timeout, erro de conexão, chave ausente e saída interrompida por limite.

A suíte emitiu um aviso de depreciação do TestClient do Starlette sobre HTTPX. Os testes passaram; não foi necessária mudança de biblioteca HTTP para a versão 0.1.

## Navegador: o que foi real e o que foi simulado

React, Vite, proxy HTTP, FastAPI, autenticação e SQLite foram reais. Apenas o provedor de IA foi substituído por `backend/tests/e2e_server.py`. Suas mensagens começam com **RESPOSTA SIMULADA DE TESTE**. Esse servidor nunca é usado por `scripts/start.sh`.

O navegador verificou: token incorreto, login correto, envio/resposta, erro de cota mantendo rascunho, tema persistente após reload, novo login e abertura do histórico persistente, páginas de configuração/administração, cancelamento e confirmação de exclusão, painel do histórico em tela móvel, envio em tela móvel e logout. Não houve exceções JavaScript durante o fluxo.

A ferramenta de navegador usada nesta execução precisou de um Chromium alternativo disponível por pacote, pois o download padrão do Playwright falhou no ambiente. Esse navegador de QA não faz parte das dependências ou do ZIP da Aurora.

## Reproduzir teste opcional de navegador

Os testes básicos do README são suficientes para o uso inicial. Este teste extra baixa navegador e dependências de desenvolvimento; não é necessário no computador fraco para executar a assistente.

1. Com a aplicação normal **parada**, instale temporariamente Playwright:

```bash
cd frontend
npm install --no-save --package-lock=false playwright
npx playwright install chromium
cd ..
```

2. No primeiro terminal, na raiz do projeto, com a venv ativada, inicie um banco temporário e provedor SIMULADO:

```bash
cd backend
AURORA_E2E_DB="$(mktemp /tmp/aurora-e2e-XXXXXX.sqlite3)" python -m uvicorn tests.e2e_server:app_factory --factory --host 127.0.0.1 --port 8000
```

3. No segundo terminal, na raiz do projeto:

```bash
npm --prefix frontend run dev
```

4. No terceiro terminal, na raiz do projeto:

```bash
node frontend/tests/browser-smoke.cjs
```

O token do servidor de testes é deliberadamente fixo e só deve ser usado com esse servidor em localhost. Não é uma credencial para a aplicação normal. Encerre ambos os processos com Ctrl+C. `npm --prefix frontend ci` restaura exatamente as dependências normais do lockfile e remove pacotes opcionais extras.

## Tamanho do build

Build observado: JavaScript aproximadamente 239 kB (75 kB gzip), CSS aproximadamente 16 kB (4,4 kB gzip). Sem fontes externas, biblioteca de ícones, imagens pesadas ou modelos locais. Não foi realizado benchmark de RAM ou carga concorrente. Não há promessa de desempenho em hardware não testado.

## Aceitação remota pendente

O código da integração Gemini é real, mas sucesso de HTTP simulado não comprova disponibilidade, cota ou autorização no Google. Para concluir a aceitação remota, configure sua chave/modelo, envie uma mensagem pelo aplicativo normal e confirme a resposta. Consulte custos e limites no projeto Google antes de gerar conteúdo. Nenhuma versão seguinte foi implementada.

## Correção de configuração em 11/10/2026

Corrigido o caminho de leitura de backend/.env: a configuração usava a pasta principal do projeto. Dois testes adicionais verificam que a raiz é backend e que o arquivo é lido mesmo quando o terminal está em outra pasta. A suíte Python completa passou com 30 testes após a correção.
