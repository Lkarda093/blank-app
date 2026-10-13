# Aurora 0.6.1 — chat compacto e resposta progressiva

Atualize no Codespace após parar o servidor com Ctrl+C:

```bash
cd /workspaces/blank-app/aurora-v0.1
```

```bash
git pull --ff-only origin aurora-v0.1
```

```bash
bash scripts/start.sh
```

Atualize o navegador com Ctrl+Shift+R. O cabeçalho mostra v0.6.1. Não há novas dependências ou mudança de schema do banco nesta correção.

## Interface

- O painel de arquivos não aparece quando a conversa não tem anexos.
- Arquivos anexados ficam em itens compactos com seleção, prévia e desanexação; contagens técnicas saíram da área principal.
- A autorização para usar o texto na próxima pergunta permanece explícita.
- Formatos, limites de upload e informações da extração ficam em seções que o usuário pode abrir.
- Há feedback durante a leitura do arquivo; arquivo vazio e arquivo acima do limite geram avisos diferentes.
- Ações secundárias da última resposta ficam em Mais opções; copiar continua acessível.

Não existe tamanho mínimo arbitrário em bytes: arquivos precisam conter texto válido. Mantêm-se os limites da 0.4: até 3 MiB por original, 30 páginas por PDF, 24 mil caracteres extraídos por arquivo/pergunta e no máximo três arquivos selecionados. A Biblioteca aceita 20 documentos e 10 MiB no total. PDF escaneado ainda exige OCR externo. Limites não foram aumentados para evitar aumentar uso de memória e contexto/cota.

## Resposta progressiva

O chat usa o endpoint `streamGenerateContent` do Gemini. O texto recebido aparece antes da conclusão, com estados de preparação de contexto, espera pelo modelo, recebimento de texto e troca de modelo. A resposta final mantém formatação, referências e indicação do modelo efetivo.

Foi removida a consulta de contexto que ocorria antes de todo envio: a interface usa a revisão carregada e o servidor a valida. Se estiver desatualizada, a interface recupera o contexto e permite reenvio revisado. Atualizações após a resposta são feitas em paralelo. Trechos em andamento usam texto simples e atualização agrupada para evitar reprocessar Markdown a cada fragmento. O modo Curta usa até 1.536 tokens de saída no streaming; os demais mantêm 4.096.

Não se promete um número fixo de segundos ou ganho percentual: o tempo do primeiro texto e a conclusão dependem do serviço, modelo, contexto e resposta. A melhoria comprovada é receber e apresentar texto antes de finalizar, além de reduzir uma chamada de preparação. Não foi usada a chave real do proprietário nos testes.

## Falhas e histórico

O servidor grava um único par de mensagens somente após a resposta concluir e ser validada. Reenvio com o mesmo identificador recupera a resposta já gravada. O endpoint JSON anterior permanece disponível.

Troca por cota 429 ou 500/503 persistente permanece limitada à lista autorizada, três modelos e 70 segundos no total. Depois de receber texto parcial, não há troca automática nem uma nova geração para ocultar uma falha.

Trechos interrompidos aparecem como Resposta incompleta e não são gravados no histórico. A pergunta permanece no rascunho. Se perder a conexão após a gravação mas antes da confirmação, confira o histórico antes de reenviar. Ao fechar o fluxo durante a geração, a tarefa é cancelada e o lock é liberado; isso não garante que o Google não tenha consumido cota.

## Testes

Testes Python de parser/contrato Gemini, retry antes do streaming, falhas/truncamento/bloqueio, autenticação, persistência idempotente, fallback e cancelamento. Testes JavaScript de fragmentação de JSON/Unicode, erros e finalização. Fluxo Chromium verifica um trecho visível enquanto a geração ainda está ativa e uma interrupção que preserva o rascunho sem salvar resposta parcial. Todos usam provedor simulado, sem cota real.
