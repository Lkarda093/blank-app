# Aurora 0.4 — documentos no chat e Biblioteca

A 0.4 torna PDF/TXT e Biblioteca funcionais, preservando a interface Cosmic UI, o chat, a troca de modelos e os controles de dados. A pasta e a ramificação continuam chamadas `aurora-v0.1`. Não renomeie a pasta nem recrie o `.env`.

## Atualizar no Codespaces

Pare a Aurora no terminal com **Ctrl + C**. Execute um comando por vez:

```bash
cd /workspaces/blank-app/aurora-v0.1
```

```bash
git pull --ff-only origin aurora-v0.1
```

Instale a nova dependência de extração no ambiente existente:

```bash
.venv/bin/python -m pip install -r backend/requirements.txt
```

```bash
npm --prefix frontend ci
```

```bash
bash scripts/start.sh
```

Abra a porta **5173**, mantendo-a privada, e recarregue com **Ctrl + Shift + R**. O cabeçalho mostra **v0.4 · Cosmic UI**. Use a sessão/token existente. Não altere a chave Gemini ou a lista de modelos por causa desta atualização.

Se o Git apresentar alterações locais/conflitos, pare e copie a mensagem de erro. Não execute `reset --hard` nem apague seus dados.

## Primeiro documento

1. Abra um chat. Clique em **Arquivos**, no **+** ou em **Analisar Arquivos** na página inicial.
2. Escolha um PDF com texto selecionável ou um TXT UTF-8. O arquivo é salvo na Biblioteca e anexado ao chat.
3. Em **Documentos desta conversa**, abra a lupa para conferir a prévia do texto. Navegue pelas páginas do PDF.
4. Marque os documentos que devem ser usados na próxima pergunta. Até três arquivos e 24 mil caracteres no total.
5. Marque **Autorizo enviar ao Gemini o texto dos documentos selecionados nesta pergunta**.
6. Escreva `Resuma o documento e indique as páginas que sustentam o resumo` e envie.
7. As referências indicadas pelo modelo aparecem abaixo da resposta; clique para abrir a página. Confira se o trecho realmente sustenta a informação.

A autorização é desmarcada após uma resposta com documentos. Confira a seleção e autorize novamente na próxima pergunta. Trocar a seleção também exige nova autorização. Reabrir uma conversa não seleciona documentos automaticamente.

O original fica no servidor; somente o texto extraído selecionado entra no contexto do Gemini, junto da pergunta, preferências autorizadas e histórico recente. O original não é enviado à API Gemini. Fazer upload, pesquisar e abrir a prévia não chama o Gemini.

Os números são das páginas físicas do PDF, podendo diferir da numeração impressa. TXT usa uma seção única, identificada como página 1 nas referências. As referências são indicadas pela IA: o servidor verifica que o rótulo e a página existem entre os textos enviados, mas não comprova a correção semântica da resposta. Referências inválidas ou ausentes geram aviso. Páginas sem texto são informadas e não têm seu conteúdo visual analisado.

## Biblioteca

A Biblioteca lista apenas arquivos reais enviados por você. Permite busca por nome, filtros PDF/TXT, grade/lista, prévia, download do original, anexação à conversa atual ou nova e exclusão com confirmação.

Enviar pela Biblioteca guarda o arquivo sem enviá-lo à IA. Use **Anexar à conversa atual** ou **Anexar em nova conversa**; revise a seleção e autorize no chat. Arquivos de conteúdo idêntico são reutilizados, evitando duplicação de armazenamento.

**Desanexar** remove o vínculo com a conversa e conserva o arquivo na Biblioteca. **Excluir arquivo** remove o original, o texto extraído e seus vínculos em todas as conversas. Respostas antigas e backups anteriores permanecem; referências a um arquivo excluído ficam indisponíveis. Excluir uma conversa conserva seus arquivos na Biblioteca.

## Limites iniciais

| Item | Limite |
| --- | --- |
| Tipos | PDF com texto e TXT UTF-8 |
| Arquivo | 3 MiB (aproximadamente 3 MB) |
| PDF | Até 30 páginas físicas |
| Texto por arquivo | Até 24.000 caracteres |
| Biblioteca | Até 20 documentos, 10 MiB de originais |
| Seleção por pergunta | Até 3 documentos e 24.000 caracteres extraídos no total |
| Contexto total | 40.000 caracteres, incluindo pergunta, texto anexado e histórico recente |
| Backup JSON | Até 32 MiB |

Arquivos grandes, vazios, malformados, binários com extensão TXT, PDFs protegidos por senha e PDFs inteiramente sem texto são rejeitados com uma mensagem clara. Não há OCR, leitura de imagens, DOCX, planilhas, pastas ou geração de documentos nesta etapa. A prévia de texto não preserva o layout e pode ter diferenças em tabelas, colunas e acentos.

## Histórico, migração e backups

Na primeira inicialização de um banco schema 1 ou 2, o sistema cria uma cópia SQLite `before-upgrade-v0.4-*.sqlite3` na pasta `backups` ao lado do banco, antes de criar as tabelas de documentos e definir schema 3. Reinícios seguintes não repetem a migração. Não faça downgrade usando o banco schema 3; para voltar à versão anterior, preserve o banco atual e use a cópia compatível com aquela versão.

Em **Configurações → Dados**, o backup completo agora inclui arquivos originais, texto extraído, anexos por conversa, referências, identidade de reenvio, conversas e preferências. Não inclui chave, token ou sessões. Contém seus dados sem criptografia; guarde-o fora do Codespace. Para um banco que exceda o limite JSON, use a cópia manual de SQLite descrita no README.

Backups JSON antigos (schema 2) continuam aceitos. Como não contêm Biblioteca, restaurá-los apaga os documentos atuais após confirmação e preserva uma cópia de recuperação. A prévia mostra as quantidades de documentos atuais e do arquivo.

Os backups novos (schema 3) exigem a 0.4 ou posterior compatível. A restauração valida tamanho, hashes, relações e reextrai os originais para conferir o texto. A validação tem um orçamento de tempo; PDFs que exigem processamento além dos limites são recusados. Nenhuma substituição acontece antes da validação, revisão e confirmação.

## Validação e limites conhecidos

Os testes usam PDFs reais gerados para QA, TXT, API e SQLite reais; apenas o serviço Gemini é simulado. O contrato HTTP do adaptador real foi verificado, inclusive com troca de modelo e texto selecionado preservado. A primeira resposta semântica com seu Gemini precisa ser conferida depois de atualizar, sujeita às cotas do seu projeto.

O parser PDF é executado em um processo separado, com limite de 12 segundos e, no Linux/Codespaces, 256 MiB de memória virtual e 8 segundos de CPU. Não depende de modelos locais, OCR, fontes externas ou ferramentas de execução do assistente. A única dependência nova de produção é `pypdf`.

Testes nesta entrega: ver [VALIDACAO_0.4.md](VALIDACAO_0.4.md). A versão encerra no escopo autorizado; novas etapas dependem de nova autorização.
