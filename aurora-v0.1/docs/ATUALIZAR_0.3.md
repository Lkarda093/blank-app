# Atualizar para Aurora 0.3

A 0.3 melhora a interface e mantém os recursos da 0.2. A pasta e a ramificação continuam chamadas `aurora-v0.1`. O `.env`, a chave Gemini, o token e o histórico existentes são preservados. Não há novas dependências de produção nem mudança no esquema do banco.

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

Abra a porta **5173**, mantenha-a privada e recarregue com **Ctrl + Shift + R**. A identificação no cabeçalho deve mostrar **v0.3**. Use o mesmo token se a sessão pedir uma nova entrada.

Se o Git indicar alterações locais ou conflitos, pare e copie somente a mensagem de erro. Não execute `reset --hard` nem apague seus arquivos.

## O que mudou

- Identidade violeta e azul escuro, inspirada nas referências visuais da Aurora; tema claro correspondente.
- Marca leve feita com CSS, sem imagens grandes, bibliotecas de ícones ou fontes externas.
- Navegação com nomes visíveis no computador; barra inferior com nomes e ícones no celular.
- Histórico à direita no computador; painel que abre pelo botão no cabeçalho em telas até 900 pixels.
- Painel móvel com foco do teclado contido, fechamento por Escape e retorno ao botão que o abriu.
- Botões explícitos “Exportar TXT” e “Exportar JSON”, título e campo de renomeação mais claros.
- Sugestões que preenchem o campo de mensagem; você revisa e envia.
- Melhor espaçamento e leitura nas configurações, mensagens e controles de backup.
- Preferência de tema e opção de movimento reduzido respeitadas.

## Confira depois de atualizar

1. Abra uma conversa antiga, envie uma mensagem e confira a resposta.
2. Renomeie e exporte em TXT/JSON.
3. Confira Configurações e Administração e baixe um backup.
4. Alterne o tema, recarregue e confira se a escolha permaneceu.
5. Em tela pequena, abra e feche o histórico pelo botão do cabeçalho.

A suíte automatizada e o navegador usam IA simulada, explicitamente identificada. A resposta real no seu Codespace depende da chave, modelo e cota existentes. Esta versão não acrescenta anexos, voz, plugins, outros provedores ou mascote animada. Documentos estão planejados para a 0.4, sujeita a autorização.
