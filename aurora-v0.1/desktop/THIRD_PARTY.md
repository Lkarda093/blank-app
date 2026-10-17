# Componentes de terceiros

O launcher e os adaptadores desta entrega são código novo do projeto Aurora. Nenhum arquivo-fonte dos projetos Jarvis/OpenClaw foi incorporado. As referências de planejamento não significam derivação de seu código.

Dependências diretas novas:

- pywebview 6.1 — Roman Sirokov e contribuidores, BSD-3-Clause. Fonte: https://github.com/r0x0r/pywebview . Licença: https://github.com/r0x0r/pywebview/blob/6.1/LICENSE . A instalação pip preserva os metadados/licença do pacote. Uma futura distribuição binária deve incluir seus avisos e os das dependências transitivas.

Motores opcionais obtidos separadamente pelo proprietário:

- llama.cpp — Georgi Gerganov e contribuidores, MIT. https://github.com/ggml-org/llama.cpp/blob/master/LICENSE . A Aurora executa o servidor via subprocesso e usa sua API; binários/DLLs não são redistribuídos nesta entrega.
- Ollama — contribuidores Ollama, MIT. https://github.com/ollama/ollama/blob/main/LICENSE . Instalação separada e conexão por HTTP local.
- Llama — Meta, licença própria da versão. Pesos não incluídos. https://github.com/meta-llama/llama-models . Um arquivo GGUF convertido mantém obrigações aplicáveis ao modelo e pode ter avisos do conversor.

React, FastAPI, SQLite, httpx, pypdf e outras dependências da Aurora continuam descritos nos manifests e nos respectivos pacotes. Este inventário não substitui os textos de licença distribuídos pelos projetos.
