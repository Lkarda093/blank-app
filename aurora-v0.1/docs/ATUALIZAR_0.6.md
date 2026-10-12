# Aurora 0.6 — perfis, projetos e continuidade

Esta atualização reúne as etapas 0.5 e 0.6. Mantém o chat Gemini, documentos e troca de modelos da 0.4, e acrescenta perfis, projetos, memória editável, resumos revisados, busca literal em documentos e melhorias do chat. Não inclui pesquisa web, ferramentas externas, voz ou controle do computador.

## Atualizar no Codespace

Pare a aplicação com Ctrl+C. Execute um comando por vez:

```bash
cd /workspaces/blank-app/aurora-v0.1
```

```bash
git pull --ff-only origin aurora-v0.1
```

```bash
.venv/bin/python -m pip install -r backend/requirements.txt
```

```bash
npm --prefix frontend ci
```

```bash
bash scripts/start.sh
```

Abra a porta 5173, mantenha-a privada e atualize com Ctrl+Shift+R. O cabeçalho mostra v0.6. A chave Gemini e o token continuam no backend/.env; não é necessário copiá-los para o código.

O banco passa ao schema 4. Antes de atualizar bancos dos schemas 1, 2 ou 3, é criada uma cópia SQLite em backend/data/backups (ou na pasta backups junto ao banco configurado). A migração é aditiva. Não apague o banco ou reinstale o Codespace para atualizar.

## Perfis da Aurora

Existem cinco perfis prontos: Aurora Geral, Estudos, Escrita, Programação e Arquitetura e Urbanismo. Use um perfil no chat ou personalize uma cópia. Perfis personalizados têm nome, descrição e instruções editáveis; até 30 podem ser salvos. As instruções, com limite de 3 mil caracteres, são enviadas ao Gemini quando o perfil é usado. Nenhum perfil ganha acesso a ferramentas por descrever uma ação nas instruções.

A seleção fica salva por conversa. Excluir um perfil personalizado faz suas conversas voltarem à Aurora Geral; respostas anteriores conservam o nome do perfil que as produziu. Edições valem para próximas respostas.

## Contexto no chat

Abra **Contexto**, acima do campo de mensagem, para escolher perfil, projeto e resposta curta/equilibrada/detalhada. A seleção de projeto não apaga mensagens ou anexos anteriores. Abra um novo chat se quiser separar assuntos. O seletor de modelo Gemini permanece independente do perfil.

As respostas agora apresentam Markdown, listas, tabelas, links e blocos de código. Há botões de copiar resposta/código e, na última resposta, atalhos que preenchem o campo para resumir, detalhar ou continuar. O usuário revisa e envia o pedido; o atalho não chama a API sozinho. HTML e imagens externas geradas pelo modelo não são executados/carregados.

## Projetos e memória

Em **Projetos e memória**, crie até 50 projetos com nome e objetivo. O objetivo orienta as conversas vinculadas ao projeto. Abra um novo chat nele ou vincule uma conversa pelo painel Contexto. As conversas são listadas com paginação; documentos da Biblioteca podem ser vinculados sem duplicar os arquivos. Vincular um arquivo ao projeto não envia seu texto ao Gemini: anexe, selecione e autorize no chat.

Na aba **Memórias**, salve decisões, restrições e pendências. Escolha entre memória geral e memória de um projeto. O salvamento exige autorização explícita de uso nas respostas. Até 100 memórias, com 1.000 caracteres cada; no máximo 8.000 caracteres de memórias ativas por envio. Se ultrapassar, a API recusa antes de chamar o Gemini e pede para reduzir/desativar memórias.

A Aurora usa memórias gerais e somente as do projeto atual. Você pode editar, desativar ou apagar cada memória. Em Contexto, pode desativar memórias e resumo para uma conversa. As preferências pessoais existentes em Configurações são independentes e têm seu próprio controle.

Excluir um projeto apaga suas memórias e vínculos. Conversas, mensagens e documentos originais permanecem. Dados já presentes nas mensagens e cópias de backup não são apagados pela exclusão de uma memória.

## Continuidade de conversas longas

Em Contexto → Resumo de continuidade, escreva decisões e pendências ou clique **Gerar sugestão de resumo**. Essa operação consome uma chamada ao modelo escolhido, usando o resumo anterior e um lote de até 30 mil caracteres de mensagens ainda não resumidas. Não envia documentos originais nem busca outras conversas. As respostas existentes na conversa podem conter informações dos arquivos analisados antes.

Revise e salve para aplicar. A sugestão não substitui automaticamente a memória. Se houver mensagens restantes, gere o próximo lote após salvar. Uma sugestão acima de 5 mil caracteres é recusada sem alterar os dados. Resumos podem omitir nuances; confira os fatos importantes.

Ao responder, a Aurora usa o resumo aprovado e até dez interações posteriores, dentro do orçamento de 40 mil caracteres de contexto montado pela aplicação, incluindo instruções de perfil, memória e documentos. O histórico completo fica salvo e exportável. Ao desativar memórias, volta a usar as interações recentes sem resumo. Há um aviso no editor quando mais de dez interações ainda não estão resumidas.

## Rascunhos e documentos

O texto não enviado é salvo neste navegador por conversa e por instalação da Aurora. Recarregar retoma a última conversa e seu rascunho. A seleção/autorização dos documentos deve ser conferida novamente. Rascunhos não entram no backup do servidor e permanecem no navegador ao sair da conta; use seu dispositivo pessoal ou limpe os dados do site para removê-los. Se o navegador bloquear armazenamento, um aviso aparece. Restaurar um backup limpa os rascunhos locais para evitar associá-los aos dados substituídos.

Em Biblioteca → **Buscar dentro dos documentos**, procure uma expressão literal no texto extraído. O resultado mostra trecho e página, com prévia clicável. A busca não chama o Gemini; não é busca semântica e continua sem OCR.

## Backup e validação

O backup JSON schema 4 inclui perfis personalizados, projetos, memórias, vínculos de documentos, contexto por conversa, resumos e identificação do perfil das respostas. Backups antigos schemas 2 e 3 continuam aceitos; restaurá-los substitui o workspace atual e deixa os novos recursos vazios/padrão. A restauração mantém a cópia de recuperação e exige autorização adicional para os dados de personalização incluídos.

Teste: crie um projeto, salve uma memória nele, escolha um perfil, envie uma pergunta, recarregue com um rascunho e confira a continuidade. Testes automatizados usam Gemini simulado: o comportamento semântico com seu modelo real deve ser conferido, sujeito às cotas da conta.
