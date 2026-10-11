# Iniciar Aurora 0.1

Abra um novo Codespace na branch aurora-v0.1. A instalação de dependências ocorre automaticamente na criação do contêiner. Aguarde terminar.

No terminal:

```bash
cd /workspaces/blank-app/aurora-v0.1
.venv/bin/python scripts/configure.py
bash scripts/start.sh
```

Digite sua chave Gemini somente no configurador, nunca no GitHub. Informe um modelo de texto disponível na sua conta. Se não souber o modelo, deixe vazio e execute `.venv/bin/python scripts/list_models.py`; depois preencha GEMINI_MODELS em backend/.env.

Abra a porta 5173 como privada. Entre com AURORA_OWNER_TOKEN, localizado em aurora-v0.1/backend/.env. Não use a chave Gemini na tela de login.

A Aurora antiga permanece na raiz. O projeto novo está na pasta aurora-v0.1. Não houve migração de dados. Detalhes e testes: aurora-v0.1/README.md e aurora-v0.1/docs/VALIDACAO.md.

A chamada real ao Gemini exige sua chave e está pendente. Modelos e cotas dependem de sua conta.
