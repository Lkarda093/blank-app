# Atualizar sua Aurora para 0.2

Use o mesmo Codespace **improved waddle**, a mesma branch `aurora-v0.1` e a mesma pasta `aurora-v0.1`. O nome da pasta foi mantido para preservar o caminho dos seus dados. A versão exibida no aplicativo será **0.2**.

## Instalação

1. No terminal onde Aurora está rodando, pressione **Ctrl + C**. Se não estiver rodando, prossiga.
2. Execute um comando por vez:

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

3. Abra a porta **5173**, privada, e recarregue a página com **Ctrl + Shift + R**.
4. Entre com o mesmo `AURORA_OWNER_TOKEN` do seu arquivo `backend/.env`.
5. Se desejar, marque **Manter acesso por 7 dias neste dispositivo**. Não marque em computador compartilhado.

A chave Gemini, o modelo configurado e o token existentes continuam no seu `.env`, que não é enviado ao GitHub. Não execute `configure.py` novamente para atualizar. Nenhuma dependência Python foi adicionada. Não é necessário criar outro Codespace nem reconstruir o contêiner.

Se o Git informar conflito ou alterações locais, pare e envie somente a mensagem de erro. Não use `git reset --hard`, não apague o `.env` e não apague a pasta de dados.

## Histórico e proteção da migração

Na primeira inicialização da 0.2, o banco SQLite da 0.1 recebe tabelas adicionais para preferências, sessões e controle de versão. As conversas e mensagens existentes são preservadas. Antes da migração, o sistema gera uma cópia SQLite em:

```text
backend/data/backups/before-upgrade-v0.2-IDENTIFICADOR.sqlite3
```

Esse caminho considera `AURORA_DB_PATH=data/aurora.sqlite3`, o padrão. Se você personalizou o caminho, a cópia fica na pasta `backups` ao lado do banco. Arquivos SQLite antigos são recuperados manualmente com a aplicação parada; o formulário de restauração recebe somente o novo backup completo JSON.

## Como usar as novidades

### Conversas

- Abra uma conversa. Acima das mensagens aparecem **Renomear**, **Texto** e **JSON**.
- Renomear altera somente o título; ele não altera as mensagens.
- Texto e JSON exportam todas as mensagens daquela conversa, incluindo páginas anteriores.
- Na barra lateral, digite no campo de busca e clique **Buscar**. A busca consulta título, mensagens do usuário e respostas.
- No celular, primeiro abra o histórico pelo botão de menu no canto superior direito.

### Preferências

- Abra **Configurações** pelo ícone de ajustes na barra esquerda.
- Preencha seu nome, estilo de resposta e orientações pessoais.
- Marque a autorização e clique **Salvar e usar preferências**.
- Você pode alterar, exportar ou apagar essas informações.
- Nenhuma preferência é extraída automaticamente do chat. As preferências salvas passam a ser enviadas ao Gemini nas próximas mensagens, inclusive em outras conversas.

### Backup

- Abra **Administração** pelo ícone de escudo na barra esquerda.
- Clique **Baixar backup completo**.
- Guarde o arquivo JSON em um local protegido fora do Codespace.

O backup completo contém conversas, mensagens e preferências. Ele não inclui chave Gemini, token, sessões ou configurações do servidor. O arquivo é legível e não tem criptografia própria. Exportar uma conversa ou preferências isoladas serve para leitura; esses arquivos não são backups completos restauráveis.

### Restauração

- No painel administrativo, selecione um **backup completo JSON da Aurora 0.2**.
- Confira os números de conversas/mensagens atuais e do arquivo.
- Se houver preferências no arquivo, confira-as e marque a autorização para restaurá-las.
- Digite **RESTAURAR** e clique **Confirmar restauração**.

A operação substitui o conjunto inteiro de conversas e preferências. Ela não mescla arquivos. Antes de substituir, Aurora grava uma cópia de recuperação dos dados atuais. Se não conseguir preservar essa cópia, a restauração não prossegue.

Se os dados mudarem depois da prévia, a operação é recusada: clique **Atualizar prévia**, confira novamente e confirme. A restauração também é recusada durante uma resposta em andamento. Até você confirmar, escolher um arquivo não altera nada.

As cópias de recuperação aparecem em **Cópias anteriores à restauração**. Para desfazer: baixe a cópia anterior e restaure esse arquivo pelo mesmo formulário. As 20 mais recentes aparecem na tela; as mais antigas continuam na pasta de backups. Não há exclusão automática dessas cópias.

### Acesso

A 0.2 mantém a sessão ao recarregar. Sem marcar a opção de 7 dias, a sessão dura no máximo 12 horas e o cookie não pede persistência após fechar o navegador. Alguns navegadores podem recuperar cookies de sessão ao restaurar abas; para encerrar explicitamente, use **Sair**.

Com a opção marcada, o cookie expira em até 7 dias. O prazo não se renova a cada mensagem. A sessão também funciona após reiniciar o servidor. Trocar o token no `.env` e reiniciar invalida as sessões anteriores. Limpar os cookies, mudar o domínio do Codespace ou usar outro navegador exige novo login.

## Limites da 0.2

- Um proprietário e um processo FastAPI; portas privadas.
- Backups JSON até 16 MiB, 10.000 conversas e 100.000 pares. Para dados maiores, use a cópia manual SQLite com o servidor parado.
- O login possui proteção básica: 5 falhas em um minuto bloqueiam novas tentativas por até um minuto naquela instância. Não substitui proteção de produção.
- A busca é uma busca literal por trecho, com comparação Unicode sem distinguir maiúsculas/minúsculas; não faz busca semântica nem remove acentos.
- Preferências personalizam o contexto enviado; o modelo pode não seguir todas as orientações exatamente.
- Voz, documentos, avatar, pesquisa web, plugins, outros provedores e agente local ficam para versões futuras autorizadas.
