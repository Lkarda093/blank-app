# Atualizar para Aurora 0.3

A 0.3.1 corrige a composição visual da interface e mantém os recursos da 0.2. A pasta e a ramificação continuam chamadas `aurora-v0.1`. O `.env`, a chave Gemini, o token e o histórico existentes são preservados. Não há novas dependências de produção nem mudança no esquema do banco.

## Atualização no Codespaces

No terminal que executa a Aurora, pressione **Ctrl + C**. Execute um comando por vez:

```bash
cd /workspaces/blank-app/aurora-v0.1
```

```bash
git pull --ff-only origin aurora-v0.1
```

```bash
npm --prefix frontend ci
```

```bash
bash scripts/start.sh
```

Abra a porta **5173**, mantenha-a privada e recarregue com **Ctrl + Shift + R**. A identificação no cabeçalho deve mostrar **v0.3 · Cosmic UI**. Use o mesmo token se a sessão pedir uma nova entrada.

Se o Git indicar alterações locais ou conflitos, pare e copie somente a mensagem de erro. Não execute `reset --hard` nem apague seus arquivos.

## Correção visual 0.3.1 — Aurora Cosmic UI

A primeira entrega 0.3 foi revista após o proprietário fornecer o texto conceitual e seis referências visuais. A composição foi refeita: lateral esquerda com marca, pesquisa, novo chat, navegação e histórico; saudação à esquerda com nome autorizado, data/hora local, seis cartões, fileira de provedores, caixa de mensagem e cinco ações rápidas. A paisagem noturna é um SVG vetorial leve, com estrelas e montanhas; não é a mesma imagem raster da referência.

### Controles reais

- Chat Gemini e todas as funções da 0.2 preservados.
- Renomeação e exportações na conversa aberta.
- Pesquisa e histórico agrupado por data; fixação de conversas neste navegador.
- Barra lateral recolhível em desktop e menu móvel com foco contido/Escape.
- Histórico à esquerda por padrão, ou painel direito em Configurações → Aparência, sem duplicar listas. A escolha fica neste navegador.
- Configurações concentra Geral, Aparência, Modelos de IA, Plugins, Conta e Dados.
- Preferências pessoais em Geral, tema claro/escuro/automático, três cores de destaque e efeitos decorativos em Aparência.
- Modelo preferido neste navegador em Modelos de IA, restrito à lista autorizada pelo servidor.
- **Backup e restauração em Configurações → Dados**, substituindo o acesso separado Administração.
- Saudação usa o nome salvo com consentimento. Não há nome pessoal inserido no código.
- Data/hora usa o fuso do navegador. Não representa agenda ou evento.
- Ações rápidas preenchem pedidos de texto e aguardam seu envio. Não anexamos ou analisamos imagens nessa etapa.

### Páginas preparadas para expansão

Agentes e IAs mostra Gemini configurado, cuja disponibilidade é verificada no envio. Outros provedores estão explicitamente não integrados. Biblioteca tem filtros e alternância de visualização, mas não possui arquivos de exemplo nem permite upload. Ferramentas/Plugins e Computador mostram status de desenvolvimento, sem controles falsos de conexão ou execução. Organização encaminha para o backup real e explica os controles existentes.

Filtros e navegação dessas páginas funcionam; a execução dos módulos anunciados depende de versões futuras. Anexos, arquivos, imagem e pesquisa no compositor abrem um aviso de desenvolvimento. O botão Ferramentas abre sua página.

A biblioteca, plugins, reconhecimento de documentos, voz, geração de mídia e acesso ao computador não foram implementados nesta correção. Os módulos secundários são carregados sob demanda. Não foram adicionadas dependências de produção, fontes externas ou modelos locais.

## Confira depois de atualizar

1. Abra uma conversa antiga, envie uma mensagem e confira a resposta.
2. Renomeie e exporte em TXT/JSON.
3. Confira Configurações → Dados e baixe um backup.
4. Alterne o tema, recarregue e confira se a escolha permaneceu.
5. Em tela pequena, abra e feche o menu/histórico pelo botão do cabeçalho.

A suíte automatizada e o navegador usam IA simulada, explicitamente identificada. A resposta real no seu Codespace depende da chave, modelo e cota existentes. Esta versão não acrescenta anexos, voz, plugins, outros provedores ou mascote animada. Documentos estão planejados para a 0.4, sujeita a autorização.

## Correção de falhas intermitentes do Gemini

O adaptador repete somente respostas HTTP 500 e 503, com até três tentativas e esperas de 0,75 e 1,5 segundo. Há um limite total de 65 segundos, inferior ao timeout do navegador. Respostas bem-sucedidas, cota (429), modelo não encontrado, timeouts e falhas de conexão não são repetidos automaticamente.

Se persistir a falha, o aviso mostra o código HTTP e o número de tentativas. Isso não garante disponibilidade do Google. Nenhuma troca de modelo ou chave é realizada. As tentativas adicionais são chamadas reais ao provedor, sujeitas às condições da conta. Uma resposta bem-sucedida continua gerando um único par de mensagens no histórico.

Para aplicar esta correção de backend, pare com Ctrl + C, execute `git pull --ff-only origin aurora-v0.1` na pasta do projeto e inicie novamente com `bash scripts/start.sh`. Não é necessário reinstalar as dependências da interface para esta alteração.
