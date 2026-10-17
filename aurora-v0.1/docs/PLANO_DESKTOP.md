# Aurora pessoal: composição de sistemas e desenvolvimento desktop

Decisão do proprietário: uso exclusivamente pessoal, código acessível e modificável, programa para PC como próxima entrega, possibilidade futura de Android. Prioridades: custo baixo, interface limpa, estabilidade, privacidade, memória consentida e respeito ao hardware disponível. Desenvolvimento assistido por IA; não treinamento de um modelo fundacional.

## Seleção de componentes

| Componente | Decisão e justificativa | Situação |
|---|---|---|
| Aurora React/FastAPI/SQLite | Preservar interface, histórico, documentos, memórias e projetos. Evita migrar os mesmos dados entre vários sistemas. | Existente e reutilizado |
| pywebview | Janela desktop com WebView2 no Windows, mantendo backend Python; dispensa incorporar um Chromium completo como parte da Aurora. Código BSD-3-Clause. | Dependência integrada |
| llama.cpp | Motor aberto MIT, executável local para modelos GGUF. Processo gerenciado pelo desktop com caminho escolhido pelo proprietário. | Adaptador e ciclo de vida implementados; binário/modelo externos |
| Ollama | Alternativa MIT com API local, facilita instalar e testar modelos. | Adaptador implementado; instalação separada |
| Llama | Pesos de modelos sob licença própria da Meta; candidato 1B/3B quantizado, português deve ser medido. | Nenhum peso baixado ou redistribuído |
| isair/Jarvis | Referência de voz/memória; código disponível não comercial. Reutilização pessoal possível conforme licença, mas não é uma biblioteca pronta para importar inteira. | Não copiado nem integrado nesta versão |
| Couvbat/Jarvis | Referência MIT de pipeline de áudio/ações, Linux; adaptar recursos selecionados somente após testar dependências Windows. | Não copiado nem integrado nesta versão |
| bigsk1/jarvis-voice | Referência de automações e memória, licença não comercial. Escopo amplo pode adicionar serviços e consumo desnecessários. | Não copiado nem integrado nesta versão |
| OpenClaw | Candidato para conectores/dispositivos mais tarde. Não é requisito para o chat local e não deve duplicar o núcleo da Aurora. | Em avaliação |

A composição atual integra software aberto por dependências e protocolos. Não há alegação de que todos esses repositórios foram fundidos. Antes de copiar código de outro projeto: fixar commit, registrar origem e licença, adaptar uma função delimitada e testar comportamento real. Reescrever uma derivação não elimina a licença original.

## Arquitetura

A janela desktop exibe a interface compilada localmente. Um backend privado no PC guarda os dados e monta o contexto. Um adaptador envia texto ao motor local. No modo administrado, a Aurora inicia `llama-server`, espera carregar e encerra o processo ao fechar. Serviços remotos futuros terão conectores separados e escolha explícita; o modo local não passa silenciosamente para nuvem.

O armazenamento local é a fonte principal do histórico e das permissões. Notion poderá receber memórias e projetos escolhidos; Drive poderá receber arquivos e backups. Eles não substituem o processo que executa a Aurora. Uma futura versão Android local exige portar a execução e as permissões; apenas adaptar a tela não produz controle do telefone.

## Etapas e critérios

1. **Desktop local, 0.7.0-desktop.1 (esta prévia):** janela, dados próprios, motor administrado, streaming, importação do backup. Validar instalação e recursos existentes no Windows real. Não chamar de versão estável antes disso.
2. **Distribuição do programa:** instalador com Python embutido e frontend compilado; fixar binários e hashes, empacotar avisos das dependências; resolver subprocesso isolado de PDF no pacote congelado. Aceitação: instalar numa máquina sem Node/Python, atualizar, desinstalar sem apagar dados inadvertidamente.
3. **Voz local:** avaliar whisper.cpp/faster-whisper para português, síntese com voz licenciada apropriada ou voz instalada do sistema, botão falar/parar e interrupção. Começar com pressionar para falar, sem escuta contínua. Aceitação: tempo de resposta, transcrição e recursos medidos no i3 junto do modelo.
4. **Ferramentas do PC:** módulo separado de ações com entradas tipadas, diretórios escolhidos, prévia e registro. Começar por listar arquivos e salvar notas, depois operações reversíveis. Não executar comandos de shell arbitrários vindos do modelo.
5. **Conectores pessoais:** Notion, Drive e calendário com contas/permissões explícitas. API local de ferramentas pode incorporar módulos de um Jarvis ou conectores OpenClaw quando isso reduzir trabalho comprovadamente. Um único histórico de ações.
6. **Modelos e roteamento:** comparar Llama local com Gemini e outros fornecedores disponíveis. Critérios: acerto, latência, custo e privacidade. Não pressupor que uma assinatura de aplicativo libera API.
7. **Manutenção supervisionada:** coletar falhas e propostas de melhoria; produzir alterações em branch de desenvolvimento, testes e revisão. Não alterar a versão em uso nem permissões/limites de gastos automaticamente. Reinícios limitados; sempre respeitar desligamento.
8. **Android:** decidir entre cliente conectado ao PC e execução local com modelo pequeno após medição. Portar áudio e permissões nativas. Não prometer funcionamento contínuo em segundo plano nem controle de todos os apps.
9. **Identidade:** voz feminina licenciada e consistente, mascote 2D discreta animada, temas claro/escuro, movimento reduzido e interface leve.

Pesquisa web, OCR e produção de documentos permanecem no planejamento, após estabilidade desktop/voz conforme prioridade do proprietário. Não há datas ou ganho de desempenho prometidos.

## Fontes técnicas consultadas

- https://github.com/ggml-org/llama.cpp — motor, servidor e docs Android.
- https://docs.ollama.com/api/introduction — API local.
- https://pywebview.flowrl.com/guide/usage.html — janela e ciclo de execução.
- https://github.com/isair/jarvis — requisitos e limitações desktop.
- https://github.com/Couvbat/Jarvis — arquitetura e componentes de voz.
- https://github.com/bigsk1/jarvis-voice — automações e termos de uso.
- https://github.com/openclaw/openclaw — alternativa de integração entre dispositivos.
- https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct — modelo e licença.
