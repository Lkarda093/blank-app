# Contexto para continuar a Aurora

Atualizado em 17/10/2026. Ler DECISOES.md antes de alterar. Este documento resume o estado; não substitui decisões do proprietário nem aprova etapas por conta própria.

## Objetivo

Assistente pessoal, exclusivo do proprietário, leve e com interface própria no Windows. Reaproveitar o chat, biblioteca e organização existentes. O proprietário é iniciante: usar português simples e passos verificáveis. PC: i3-4130, GTX 1050 Ti 4 GB de VRAM, executando também AutoCAD, Revit, SketchUp e Inkscape. RAM total ainda desconhecida.

## Regras

- A ordem explícita do proprietário sobrepõe sugestões anteriores. Em conflito, avisar antes da mudança.
- Nenhuma execução no PC sem aprovação explícita; nenhum executor de shell arbitrário.
- Não colocar credenciais, banco ou dados pessoais no repositório. Não pedir chave pelo chat. Não salvar chave em .env, JSON ou logs.
- Perguntar limite de gasto antes de chamada paga. Nunca inferir que um modelo é gratuito. Esta entrega não autoriza nem ativa faturamento.
- Fazer backup antes de atualização e medir RAM/CPU antes/depois. Se o ambiente não permitir medir o Windows, registrar a limitação, sem substituir por números Linux ou estimativas.
- Cada entrega deve indicar mudanças, arquivos, testes antes/depois, riscos e reversão. Simulação não comprova execução real.
- Preservar Aurora Cosmic UI e temas claro/escuro. Mostrar proposta antes de mudança visual; listar remoções de tela e aguardar aprovação.
- Trabalhar em etapas. Não avançar itens da lista de espera por suposição.

## Estado atual

Base auditada: branch aurora-v0.1, commit d9f70eecb912db605c792af2f3a4f0af7110d12d, versão 0.7.0-desktop.1. Backup remoto: backup/aurora-2026-10-17-antes-correcao-1. A atualização da Correção 1 é 0.7.0-desktop.2 e deve ser revisada/testada antes de substituir a instalação pessoal.

- Backend FastAPI/SQLite; frontend React/Vite/Tailwind; launcher Python/pywebview/WebView2.
- Correção 1 implementada: modos Gemini, llama.cpp, Ollama; novas configurações começam em Gemini; existentes mantêm o provedor. Escolha explícita na janela Configurar-Aurora.cmd.
- Gemini obtém a chave do cofre do usuário Windows. Configuração exige modelo e aceite de privacidade, sem consulta automática de preços/modelos ou download de motor. Nuvem não inicia motor local.
- Backend web Windows usa o mesmo cofre. Servidores não Windows recebem chave por segredo do ambiente. O carregador recusa GEMINI_API_KEY preenchida em .env; nenhuma chave antiga é movida/apagada automaticamente. A documentação histórica que manda gravar chave em .env foi substituída pelo guia DESKTOP.md atual.
- Dados desktop em %LOCALAPPDATA%\Aurora; banco/rascunhos contêm informações pessoais. Código e dados ficam separados. O banco não é criptografado por esta entrega; o esquema não mudou.
- Chat, histórico, PDF com texto/TXT, perfis, projetos, memórias e resumos possuem implementação. Tarefas/cronogramas não possuem tabela/módulo.
- Ferramentas, Plugins e Computador são telas de desenvolvimento. Os componentes Agents/Organization antigos em Modules.jsx não são os componentes atuais da navegação. Não remover perfis/projetos por confundi-los com essas sobras.
- Sobras Streamlit na raiz e documentação histórica permanecem para revisão separada.
- Fechamento normal ainda é a única proteção de encerramento do llama-server: Correção 2 não implementada. A Aurora não administra a vida do Ollama externo.
- Nenhuma capacidade de executar ações arbitrárias, modificar o próprio código, controlar o computador ou sobreviver a desligamento foi adicionada.

## Evidência e limites

Linha de base: 158 testes Python e 10 JavaScript. Correção 1: 175 Python, 10 JavaScript e build passaram no Linux; janela e cofre simulados; sem Gemini/modelo real. RAM/CPU apenas da API de testes Linux, sem WebView2/modelo; números e escopo em DESKTOP.md. Windows real, instalação limpa, cofre real, desempenho com programas de arquitetura e chamadas Gemini ainda pendentes. Nenhum comando desta entrega executou no PC do proprietário.

## Próxima etapa

Apresentar a Correção 1 para revisão. Seguir a autorização do proprietário para a próxima etapa e para testes no Windows. Próximo trabalho técnico planejado: Correção 2, com Job Object, identificação segura de motor órfão da Aurora e logs limitados sem prompts. Não encerrar programas apenas por terem o mesmo nome de executável.

Lista de espera: tarefas/cronogramas; formatação; consolidação da documentação; limpeza Streamlit; acesso pelo celular. Uma autorização por vez.

## Fora de escopo

OpenClaw, fusão Jarvis, plugins Revit/AutoCAD, Android nativo, controle remoto do PC, mascote, voz e modelo local ligado por padrão. Também não desenvolver autossobrevivência, treinamento autônomo ou edição autônoma do código por inferência de pedidos antigos.
