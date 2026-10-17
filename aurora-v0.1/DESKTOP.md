# Aurora Desktop 0.7.0-desktop.1 — prévia para Windows

Esta é a primeira composição desktop da Aurora pessoal: interface React existente + API Python/SQLite + janela nativa pywebview + adaptadores locais llama.cpp/Ollama. O código está disponível neste repositório. Não é um instalador .exe pronto nem uma fusão completa dos projetos Jarvis. O motor llama.cpp pode ser iniciado e encerrado pela Aurora; seu binário e os pesos do modelo são obtidos separadamente.

## O que esta entrega executa

- Janela própria no Windows, sem depender de Codespaces ou hospedagem depois da instalação.
- Entrada automática na sessão local, sem expor token na interface ou gravá-lo em arquivo.
- Chat com respostas progressivas, histórico, perfis, projetos, memória, biblioteca PDF/TXT e backups existentes.
- Motor llama.cpp administrado pelo launcher: carrega um GGUF escolhido e encerra ao fechar a Aurora.
- Alternativa: conexão com Ollama já instalado. A Aurora não encerra um Ollama que não iniciou.
- Modo local sem fallback automático para Gemini; modelos Ollama marcados como remotos são recusados.
- Dados em `%LOCALAPPDATA%\Aurora`, independentes da pasta de código.

A interface usa tecnologia web dentro de uma janela nativa. O backend e o modelo executam no PC. Isso é um aplicativo desktop híbrido; não é apenas um atalho para o site publicado.

## Preparar no Windows

1. Exporte o backup da Aurora antiga em Configurações → Dados. Guarde o JSON no PC.
2. Baixe a branch `aurora-v0.1` do repositório e extraia o ZIP. Entre na pasta `aurora-v0.1` que contém este documento.
3. Instale **Python 3.12 para Windows**, incluindo o Python Launcher: https://www.python.org/downloads/windows/
4. Instale **Node.js LTS 22.12 ou superior**: https://nodejs.org/
5. Confirme que o **Microsoft Edge WebView2 Runtime** está disponível: https://developer.microsoft.com/microsoft-edge/webview2/
6. Abra `Instalar-Aurora.cmd`. Ele cria um ambiente Python na pasta do projeto, instala dependências e compila a interface. Internet é necessária nesta etapa. Se aparecer um erro, a janela permanece aberta; não considere a instalação concluída.
7. Prepare um dos motores abaixo.
8. Abra `Iniciar-Aurora.cmd` e preencha a configuração inicial. Para alterar depois, feche a Aurora e abra `Configurar-Aurora.cmd`.
9. Na janela da Aurora, importe o backup antigo em Configurações → Dados, revise a prévia e confirme. Nada é transferido automaticamente do Codespaces.

## Opção A — llama.cpp administrado pela Aurora

1. Obtenha o pacote **Windows x64 CPU** do projeto oficial: https://github.com/ggml-org/llama.cpp/releases . Extraia o pacote completo, mantendo `llama-server.exe` e suas DLLs juntos. Não escolha ARM ou um pacote CUDA para este primeiro teste.
2. Obtenha um modelo **GGUF de instruções**, inicialmente de 1B, quantizado em Q4. Llama 3.2 1B Instruct é candidato; português, velocidade e qualidade ainda precisam ser avaliados no PC. A Meta disponibiliza a ficha/licença em https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct . Arquivos GGUF convertidos por terceiros exigem verificar origem, variante e licença; o repositório não distribui pesos nem apresenta conversões como oficiais.
3. Na configuração da Aurora, selecione `Motor integrado llama.cpp`, o executável e o arquivo `.gguf`.
4. Aguarde o carregamento. A primeira carga pode demorar. Se não carregar em dois minutos, a Aurora encerra o processo que iniciou e informa a falha.

O caminho escolhido deve apontar para um executável de fonte confiável, pois ele será executado com os direitos do seu usuário. Não é necessário privilégio de administrador.

## Opção B — Ollama, preparação inicial mais simples

1. Instale o Ollama oficial: https://ollama.com/download/windows .
2. Abra o terminal do Windows e execute `ollama pull llama3.2:1b`. O download ocupa espaço e usa internet; observe os termos do modelo.
3. Mantenha o Ollama disponível e escolha `Ollama já instalado` na configuração da Aurora. Informe `llama3.2:1b`.
4. Não selecione modelos com sufixo cloud. A Aurora exige modelo instalado e recusa metadados remotos no modo local.

Nesta opção o Ollama continua sendo um processo externo. Na opção A a Aurora gerencia o processo llama.cpp. Nenhum dos motores é copiado para o repositório por esta entrega.

## Perfil inicial para o PC informado

Intel i3-4130, GTX 1050 Ti 4 GB; RAM total ainda não confirmada. O motor administrado inicia com CPU, dois threads, uma sequência e 4096 tokens de contexto. GPU fica desativada inicialmente para reduzir problemas de DLL/driver e concorrência com programas de arquitetura. Ollama decide sua própria distribuição CPU/GPU.

Respostas locais são limitadas a 768 tokens, com aviso para continuar. A montagem de contexto local aceita até 6000 caracteres (pergunta, instruções, memórias e documentos); isso é uma aproximação conservadora, não uma equivalência exata entre caracteres e tokens. Histórico antigo continua salvo. Documentos maiores ainda podem ficar na biblioteca, mas não caber numa pergunta local. O modo Gemini mantém o orçamento anterior de 40000 caracteres.

Não há promessa de respostas rápidas ou desempenho igual a Gemini/Claude. Medir: tempo até o primeiro trecho, tempo total, RAM, estabilidade e acerto em português. Modelos menores podem ser insuficientes para ferramentas complexas.

## Uso e manutenção

- Fechar a janela encerra a API local e o llama.cpp iniciado pela Aurora. Não há serviço em segundo plano nem tentativa de continuar após você desligar.
- API e motor administrado escutam somente em `127.0.0.1`; esta entrega não oferece acesso remoto pelo celular.
- Conversas: `%LOCALAPPDATA%\Aurora\aurora.sqlite3`. Configuração do motor: `%LOCALAPPDATA%\Aurora\desktop.json`.
- Preferências visuais/rascunhos ficam no armazenamento WebView2 do perfil local.
- Backups e exportações usam o diálogo de downloads do WebView2. Validar esse fluxo no Windows é parte do teste de aceitação.
- Para atualizar, feche a Aurora, substitua o código por uma versão revisada e execute novamente `Instalar-Aurora.cmd`. O diretório de dados permanece separado. Faça backup antes.
- Para voltar ao site atual, use sua instalação anterior. O desktop não altera o banco do Codespaces.

## Limites desta prévia

Ainda não inclui microfone, síntese de voz, execução de ferramentas no PC, plugins Jarvis/OpenClaw, aplicativo Android, treinamento de modelos, edição autônoma de código nem um instalador .exe independente de Python/Node. O modelo é instruído a não afirmar que executou ações externas.

Foram implementados e testados contratos HTTP de modelos locais simulados, autenticação desktop, acesso aos arquivos da interface, bloqueio de hosts externos, CSRF, resposta incompleta e regressões do backend/interface. A janela WebView2, instalação limpa, diálogos de download, modelo real e desempenho não foram executados em Windows neste ambiente Linux.

## Teste de aceitação no seu PC

1. Abrir a janela e enviar `Responda em uma frase: o que você pode fazer nesta versão?`.
2. Fechar/reabrir e conferir o histórico.
3. Renomear conversa, exportar TXT, importar um TXT e abrir sua prévia.
4. Exportar backup e verificar que o arquivo foi baixado.
5. No modo local, desligar internet após os downloads e repetir uma pergunta.
6. Fechar a Aurora e verificar que o llama-server iniciado por ela encerrou.
7. Anotar RAM do PC, demora e qualquer erro. Só então aumentar o modelo ou ativar GPU.
