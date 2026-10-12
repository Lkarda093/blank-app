# Validação — Aurora 0.4

Ambiente: Linux, Python 3.12 e Node 24, com Chromium de QA. A suíte anterior foi preservada e ampliada. Não foi usada uma chave real do proprietário.

| Verificação | Resultado |
| --- | --- |
| Testes Python | 110 casos passaram |
| Cliente JavaScript | 8 casos passaram |
| Build React/Vite | Concluído |
| PDF real de duas páginas | Texto, página, referência e download do original verificados |
| TXT UTF-8 | Acentos preservados; binários/codificação inválida recusados |
| Arquivos inválidos/limites | Vazio, extensão, tamanho, caracteres, páginas, senha, ausência de texto, timeout e limite da Biblioteca cobertos |
| Envio selecionado | Consentimento obrigatório, limite combinado, documento vinculado e nenhuma inclusão de arquivo não selecionado |
| Adaptador Gemini | Corpo HTTP real do adaptador capturado por transporte simulado; texto selecionado e instruções de documentos preservados em fallback |
| Persistência/reenvio | Modelo, seleção, referências e identidade de envio persistem; reinício e repetição não duplicam resposta |
| Migração SQLite | Bancos schema 1 e 2 preservados; cópia anterior e migração única para schema 3 |
| Backup/restauração | Originais, páginas, vínculos, referências e identidade restaurados; schema 2 aceito |
| Backup inválido | Hash, texto modificado, referência inválida, vínculo órfão e revisão antiga recusados sem substituir dados |
| Chromium | Fluxo completo anterior e novo fluxo de arquivos passaram, sem exceções JS |
| Layout | Inspeção visual de Biblioteca desktop e chat móvel com documentos; sem rolagem horizontal no fluxo testado |

## O que foi real no navegador

Frontend, upload binário, proxy Vite, extração `pypdf`, subprocesso, API FastAPI, SQLite, cookies, downloads e restauração são os componentes reais da aplicação. O provedor exclusivamente de testes retorna textos iniciados por **RESPOSTA SIMULADA DE TESTE** e citações determinísticas. O comando normal `start.sh` usa o adaptador real do Gemini.

O percurso enviou PDF, abriu a segunda página, baixou e comparou o original, exigiu autorização antes do envio, abriu referência da resposta, enviou TXT pela Biblioteca, buscou pelo nome, anexou e desmarcou o TXT, confirmou que apenas o PDF foi usado, exportou backup com dois documentos, excluiu o PDF e restaurou o arquivo com a mesma prévia. Os fluxos anteriores de login, histórico, preferências, cota/fallback, exportação, recuperação e logout também foram executados.

## Reproduzir

Na pasta do projeto:

```bash
.venv/bin/python -m pip install -r backend/requirements-dev.txt
.venv/bin/python -m pytest backend -q
npm --prefix frontend test
npm --prefix frontend run build
.venv/bin/python -m compileall -q backend/app scripts
bash -n scripts/start.sh
```

O teste de navegador continua opcional. Veja o procedimento e as variáveis de Chromium em [VALIDACAO.md](VALIDACAO.md); com Playwright e navegador de QA instalados, execute `.venv/bin/python scripts/browser_test.py`. Não instale o servidor de testes como aplicativo normal.

## Limitações

Não foi feita chamada de documentos ao Google com a chave real, avaliação de precisão semântica, benchmark de RAM/carga, OCR, teste em Safari/Firefox, leitor de tela ou dispositivo físico. Referências verificadas significam que a página existe entre os textos enviados; não comprovam que a resposta está correta. A extração pode perder organização espacial de tabelas e colunas. Limites de memória do subprocesso foram implementados para Linux; em outros sistemas, a proteção disponível pode diferir.

A suíte emite um aviso de depreciação do TestClient Starlette sobre HTTPX; não houve falha relacionada. Os arquivos de QA e capturas não fazem parte do projeto publicado.
