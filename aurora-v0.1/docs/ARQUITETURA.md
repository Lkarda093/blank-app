# Arquitetura e critérios — Aurora 0.1

## Objetivo e aceitação

Criar uma base de chat pessoal leve, com código legível e separação entre interface, API, persistência e provedor. A versão é aceita quando: o frontend compila; o backend inicia; a autenticação bloqueia acesso indevido; conversas podem ser criadas, recuperadas após reinício e excluídas mediante confirmação; o tema persiste; envios válidos são encaminhados ao adaptador Gemini; erros não expõem segredos nem salvam trocas incompletas; os testes locais passam. A aceitação da integração remota depende adicionalmente de um envio real usando a conta do proprietário.

## Decisões

| Componente | Decisão e motivo |
| --- | --- |
| Frontend | React 19, Vite 7 e Tailwind 4. Sem biblioteca grande de componentes, fontes externas ou imagens |
| Backend | FastAPI assíncrono, documentação OpenAPI automática e validação Pydantic |
| Transporte Google | HTTPX com HTTPS, timeout e chave em cabeçalho; adaptador implementa Protocol |
| Banco | SQLite nativo, chaves estrangeiras, transações, WAL e versão de schema 1 |
| Segurança | Token aleatório do proprietário em servidor; bearer apenas na memória do browser |
| Rede | Navegador → Vite `/api` → FastAPI; same origin sem CORS permissivo |
| Contexto | Até 10 pares completos mais a mensagem atual, até 40.000 caracteres |
| Confiabilidade | ID por envio; gravação do par em uma transação; sem retries automáticos |
| Concorrência | Uma geração ativa por instância, 409 para concorrentes; um worker obrigatório |
| UI | Identidade botânica discreta, histórico à direita, navegação compacta, painel móvel |

As tabelas são `conversations` e `turns`. Cada turn guarda mensagem do usuário, resposta, modelo, data e request_id. O uso de um par em uma linha torna atômica a gravação da troca. Um índice único impede duplicação local. O DELETE tem cascata para as trocas; as consultas usam parâmetros SQL.

Persistência é server-side: se o servidor está no Codespaces, o histórico está no Codespaces, não no celular. Isso é a base híbrida inicial: interface leve e persistência controlada pelo proprietário, inferência em API externa. Nenhum agente instalado no computador é necessário agora.

## Fluxo de um envio

1. React mantém o token somente em memória e cria um request_id UUID.
2. FastAPI valida autenticação, conteúdo, modelo autorizado e existência da conversa.
3. O servidor verifica se o mesmo envio já foi concluído.
4. O contexto recente é lido e limitado; a transação SQLite é fechada antes da chamada de rede.
5. O adaptador envia a solicitação ao Google. Não existem ferramentas ou funções executáveis pelo modelo.
6. Em sucesso, usuário/resposta e título são gravados atomicamente; em falha, nada é salvo.
7. React apresenta texto seguro, sem interpretar HTML. O rascunho só é limpo após sucesso.

O request_id protege repetições de envios já gravados. Não garante exatamente uma cobrança no provedor: uma queda após o Google processar e antes de gravar pode consumir cota e exigir nova chamada. O rascunho não persiste após recarregar.

## Organização futura, ainda não implementada

| Área | Módulo futuro | Fronteira prevista |
| --- | --- | --- |
| Conversas | `conversations` existente | Exportação, busca, títulos editáveis |
| Provedores | `providers` existente | Um adaptador real por serviço; sem chaves no browser |
| Memória | `memory` | Preferências opt-in, revisão, edição, exportação e exclusão |
| Conhecimento | `library` | Uploads com tamanho/tipo permitidos, origem e permissões |
| Usuários | `auth` existente; futuro `users` | Sessões e controle de papéis antes de acesso compartilhado |
| Configurações | `config.py` existente | Configuração validada; segredos separados de dados |
| Plugins | `plugins` | Manifestos, permissões mínimas e confirmação de ações |
| Voz | `voice` | Adaptadores STT/TTS; consentimento antes de enviar áudio |
| Dispositivos | `devices` | Agente separado, pastas permitidas e leitura apenas |

Não criamos pastas e endpoints vazios para aparentar funções prontas. Os módulos futuros deverão surgir com sua funcionalidade e testes em uma versão autorizada.

## Quatro memórias

1. **Histórico:** implementado por conversa, persistente e apagável. Exportação estruturada/edição ainda pendentes; backup manual do SQLite disponível.
2. **Preferências:** futuras, propostas pela assistente e salvas só após confirmação. O usuário poderá corrigir/excluir. Tema atual é preferência local simples, fora da memória de IA.
3. **Documentos:** futuros, com armazenamento de origem e autorizações. Busca semântica só será adicionada após avaliar necessidade e custo. Obsidian começa por leitura de pastas expressamente autorizadas.
4. **Erros e melhorias:** futuro registro revisável, sem segredos nem aprendizado irrestrito. Alterações no código continuarão manuais, versionadas e testadas. Agora há apenas mensagens de erro e logs operacionais mínimos.

Não há memória oculta entre conversas, treinamento automático ou modificações de produção pela IA.

## Riscos e limites

- Chave válida não assegura cota, acesso a qualquer modelo nem gratuidade. O catálogo pode mudar. O modelo fica configurável no servidor.
- SQLite e `.env` não têm criptografia própria. Proteção da conta, disco e backups cabe ao proprietário.
- Vite é servidor de desenvolvimento. Publicação em produção requer HTTPS, serviço para arquivos compilados, autenticação mais completa, limitação de requisições e revisão de implantação.
- Não iniciar vários workers/processos com o mesmo banco nesta versão. O bloqueio de geração é em memória.
- O histórico cresce em disco. A UI carrega páginas, mas não há política automática de retenção.
- O modelo pode inventar informações. Sem pesquisa web, voz ou ferramentas, não deve declarar execução de ações.
- Chave revogada ou modelo descontinuado: corrigir configuração e reiniciar; nunca fazer fallback silencioso para outro provedor pago.

## Sequência entregue

Arquitetura → configuração/autenticação → schema SQLite → rotas → adaptador Gemini → frontend → testes → documentação. Versão 0.2 depende de autorização explícita do proprietário.
