# Arquitetura e critérios — Aurora 0.2

## Escopo

A 0.2 acrescenta controle dos dados à base de chat: exportação por conversa, busca/renomeação, backup completo e restauração, preferências autorizadas e sessão no navegador. Mantém React/Vite/Tailwind, FastAPI/HTTPX e SQLite, sem novas dependências de produção. O repositório e a pasta continuam `aurora-v0.1` para manter os comandos e caminhos do proprietário.

## Critérios de aceitação

- Chat, histórico e autenticação existentes continuam funcionando.
- Migração de um SQLite com schema 1 preserva as conversas e mensagens, cria uma cópia anterior à atualização e passa ao schema 2.
- Exportação TXT/JSON contém todas as mensagens da conversa, independentemente da paginação da tela.
- Busca consulta títulos e ambos os lados da conversa como trecho literal, com casefold Unicode. `%` e `_` não são curingas.
- Preferências só são salvas mediante consentimento explícito; podem ser lidas, editadas, exportadas e apagadas. Preferências salvas entram nas próximas chamadas ao Gemini.
- Backup JSON completo contém histórico e preferências; exclui credenciais, configurações e sessões.
- Restauração valida schema, limites, identificadores, relações e datas; exige prévia vinculada ao arquivo/revisão, confirmação e consentimento para preferências.
- Mudanças depois da prévia, chamadas concorrentes, arquivo inválido e falha ao preservar a cópia anterior impedem a troca.
- Sessão continua após reload/reinício, expira e é revogada ao sair ou trocar o token.
- Interface responsiva e testes passam antes de enviar a versão ao GitHub.

## Componentes

| Componente | Responsabilidade |
| --- | --- |
| `backend/app/conversations/routes.py` | CRUD, envio, busca, renomeação e exportação |
| `backend/app/providers` | Adaptador real Gemini; Protocol com personalização opcional |
| `backend/app/auth` | Bearer para API; entrada, cookie de sessão, expiração e logout |
| `backend/app/memory/routes.py` | Preferências opt-in e composição de personalização |
| `backend/app/data/routes.py` | Snapshot, download, validação de backup e restauração |
| `backend/app/database.py` | Conexões, migração, tabelas, transações e revisão dos dados |
| `frontend/src/App.jsx` | Chat, histórico, busca, navegação e sessão |
| `frontend/src/Preferences.jsx` | Editor e consentimento de preferências |
| `frontend/src/DataPanel.jsx` | Estatísticas, backup, prévia, confirmação e recuperação |
| `frontend/src/api.js` | Requisições same-origin, cabeçalho CSRF e downloads |

## Dados e migração

Schema 1: `conversations` e `turns`. Schema 2 adiciona `preferences`, `sessions` e `metadata`. Cada turn é um par de mensagem/resposta, com request_id único por conversa. Índice e relações originais são mantidos.

O início com schema 1 cria uma cópia via `sqlite3.Connection.backup` antes da migração. O schema é alterado em transação e possui guarda contra bancos de uma versão superior. Reiniciar com schema 2 não repete essa cópia. A aplicação continua usando um único processo FastAPI.

`metadata.data_revision` aumenta em cada alteração de conversa, troca ou preferências. Login/logout não alteram essa revisão. Na prévia de restauração, um ticket HMAC vincula a revisão e o conteúdo normalizado do arquivo. A substituição exige a mesma revisão e ticket; não admite confirmação de uma prévia para outro arquivo.

O backup portátil tem formato `aurora-backup`, schema_version 2 e inclui `exported_at`, `conversations`, `turns` e `preferences`. A exportação de conversa tem outro formato e não é aceita como backup completo.

## Transações de restauração

1. Ler upload com limite de 16 MiB e validar JSON/schema antes de qualquer exclusão.
2. Verificar a confirmação RESTAURAR, ticket, revisão e consentimento das preferências.
3. Rejeitar se houver geração/operação em andamento; adquirir o bloqueio da instância.
4. Iniciar transação SQLite IMMEDIATE e conferir novamente a revisão.
5. Criar JSON de recuperação com os dados atuais, em arquivo exclusivo com modo 0600, flush e fsync.
6. Apagar/inserir histórico e preferências dentro da transação, preservando IDs do arquivo.
7. Aumentar revisão e confirmar. Erro de gravação/inserção causa rollback; a cópia anterior é mantida.

A restauração substitui o conjunto inteiro; não mescla backups. Sessões e chave/token não são restaurados nem apagados. Cópias anteriores são acessadas por UUID, nunca por caminho arbitrário fornecido pelo navegador.

## Acesso

O token do proprietário continua em backend/.env e é usado na entrada. O servidor gera um segredo aleatório distinto para o cookie; apenas o digest HMAC é persistido. O HMAC usa o token do proprietário como chave, portanto sua rotação invalida sessões anteriores após reinício.

Cookie: HttpOnly, SameSite=Strict, path /api; Secure em HTTPS e hosts públicos. Cookie sem persistência explícita e sessão de 12 horas por padrão; remember cria cookie com validade de 7 dias. O token mestre nunca é gravado em localStorage. Sair remove o registro da sessão e o cookie; a opção de lembrar não impede a revogação.

Escritas via cookie exigem X-Aurora-Request: 1 e, se houver Origin, origem correspondente ao Host. Não há CORS permissivo. Login tem limite básico de 5 falhas em um minuto por instância. Não é um sistema multiusuário nem uma solução de rate limiting distribuído.

## Memória

- Histórico: persistente, buscável, exportável, apagável e restaurável.
- Preferências: nome, estilo e notas; criadas/alteradas manualmente com autorização. Enviadas como dados de personalização adicionais ao Gemini. Excluir deixa de enviá-las nas próximas chamadas, mas não apaga chats e backups antigos.
- Conhecimento/documentos: ainda planejado, incluindo Obsidian e busca semântica.
- Erros e melhorias: ainda planejado; atualmente há apenas logs operacionais mínimos, sem aprendizado autônomo ou alterações de código pela IA.

## Limites e próximos módulos

Backup portátil: 16 MiB, 10.000 conversas e 100.000 pares, limites adicionais por campo. Para bancos maiores, cópia manual SQLite com a aplicação parada. As 20 recuperações mais recentes são exibidas; as demais permanecem em disco. Não há expurgo automático nem criptografia própria.

Busca é literal e não é semântica. Preferências não treinam o modelo. A aplicação não consulta saldo/custos do Google. Conteúdo continua texto simples. Voz, documentos, plugins, outros provedores, avatar e agente local não fazem parte da 0.2; módulos futuros dependem de autorização.

## Documentos — 0.4

`app/documents` recebe bytes sem multipart, valida nome/extensão/tamanho, extrai PDF em processo separado e grava originais BLOB e páginas JSON no SQLite. `conversation_documents` mantém vínculos; `turn_document_context` guarda seleção e referências para reenvio e histórico. A API envia ao provedor apenas textos selecionados, tratados como dados, com rótulos de página. Referências são conferidas contra páginas enviadas e expostas com prévia, sem alegação de verificação semântica.

O frontend separa Biblioteca, painel de anexos e prévia em componentes carregados sob demanda. Upload não chama o provedor. O backup schema 3 guarda documentos e contexto, valida originais e aceita leitura de schema 2. A migração para SQLite schema 3 é aditiva, com cópia anterior.


## Workspace 0.6

O módulo `app/workspace` gerencia perfis customizados, projetos, memórias consentidas, vínculos de documentos e contexto por conversa. Cinco perfis padrão ficam no código. Tabelas adicionais no schema 4 preservam a estrutura original de conversations/turns. Há cópia SQLite antes da migração.

Cada envio valida a revisão de contexto e registra perfil/projeto efetivos em turn_workspace. Reenvios devolvem a resposta salva com o mesmo contexto solicitado, mesmo após alterações ou exclusão de perfis. Memórias têm escopo global ou de projeto; desativação remove-as do contexto futuro. Um teto de 8 mil caracteres impede truncamento silencioso da memória.

Resumos são gerados em lotes, revisados e salvos explicitamente com marcador de cobertura. O histórico original não é alterado. Todas as mutações compartilham o lock de geração e invalidam as prévias de restauração. Os backups schema 4 validam relações, IDs e marcadores de resumo; schemas 2/3 são importados com valores padrão.

O frontend usa react-markdown e remark-gfm sem HTML bruto, sem carregar imagens externas e com links HTTP(S). Rascunhos são locais, separados pelo workspace_id do servidor e pela conversa; não incluem seleção ou consentimento de documentos. Busca literal de trechos opera no SQLite/texto extraído sem chamadas ao Gemini.
