# Validação da Aurora 0.6

## Verificações automatizadas

- Suíte Python anterior e novos testes de workspace: 128 casos no conjunto (125 na execução completa, seguidos dos 15 casos de workspace incluindo três adicionais). A única advertência observada é a depreciação do adaptador httpx do TestClient pela versão instalada de Starlette.
- 8 testes JavaScript do cliente HTTP: aprovados.
- Instalação limpa com `npm ci`: aprovada. Corrigidas entradas locais inválidas de versões no lockfile e adicionados react-markdown/remark-gfm, com versões resolvidas no lockfile.
- Build Vite: aprovado. Bundle principal cerca de 428 kB (133 kB gzip); módulos de gerenciamento carregados sob demanda.
- Chromium: fluxos de regressão da 0.4 e fluxo integrado de perfis/projetos/memórias, contexto enviado, rascunho após reload, Markdown, resumo revisado e backup com consentimento.

Apenas o provedor Gemini é simulado. API, autenticação, CSRF, SQLite, migração, arquivos PDF/TXT, extração, downloads, interface e restauração são reais nos testes isolados. Não foi usada a chave do proprietário nem consumida sua cota.

## Casos novos

- Perfis personalizados, seleção persistida, exclusão com retorno ao perfil geral e nome do perfil preservado nas respostas antigas.
- Memórias com consentimento, isolamento entre projetos, desativação, limite antes da chamada e rejeição de contexto desatualizado.
- Reenvio idempotente após alteração de contexto sem duplicar geração.
- Resumo gerado como prévia, salvamento revisado, cobertura por mensagens, preservação de todo o histórico, rejeição de resumo excessivo e desativação do uso.
- Projeto com documentos, busca literal por trecho/página, exclusão sem apagar originais ou conversas.
- Backup completo incluindo perfil personalizado, resumo, documentos de projeto e memórias; importação de schemas antigos; rejeição de relações órfãs antes de qualquer alteração.
- Migração de schema 3 preservando mensagens e uma única cópia de segurança; rotas protegidas por autenticação.
- Markdown sem execução de HTML, links javascript ou carregamento de imagens externas.
- Navegador em desktop e celular, sem transbordamento horizontal e sem exceções JavaScript.

## Limites e teste real pendente

O resumo não é produzido em segundo plano: usa uma chamada explícita e só passa a valer após revisão. Busca de documentos é literal, sem OCR ou embeddings. Memórias são cadastradas pelo usuário; não há aprendizado automático ou mistura de projetos. Rascunhos ficam no navegador, fora do backup.

Após atualizar o Codespace, verificar com Gemini real: resposta no perfil escolhido, lembrança de uma decisão do projeto, ausência dessa memória em outro projeto e fidelidade de um resumo de continuidade. Os testes de software não garantem correção factual do modelo.
