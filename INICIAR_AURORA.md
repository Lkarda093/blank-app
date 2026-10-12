# Aurora 0.2 — iniciar e atualizar

Se já usa a Aurora, abra [Atualizar para 0.2](aurora-v0.1/docs/ATUALIZAR_0.2.md). A branch e a pasta continuam chamadas aurora-v0.1 para facilitar a atualização e manter o caminho do histórico.

No Codespace existente, pare a aplicação com Ctrl+C e execute um comando por vez:

```bash
cd /workspaces/blank-app/aurora-v0.1
git pull --ff-only origin aurora-v0.1
npm --prefix frontend ci
bash scripts/start.sh
```

Abra a porta 5173 privada e recarregue a página. Use o mesmo token existente; a chave Gemini e o modelo ficam no backend/.env. O banco é migrado automaticamente, com cópia SQLite anterior à migração. Não apague o .env nem a pasta de dados.

Instalação nova: [README completo](aurora-v0.1/README.md). O Codespace novo nesta branch instala dependências na criação. Configure uma vez com `.venv/bin/python scripts/configure.py` e inicie com `bash scripts/start.sh`.

Novidades: busca/renomeação, exportação de conversas, preferências consentidas, backup/restauração com confirmação e recuperação, sessão lembrada opcional por 7 dias. Consulte [validação](aurora-v0.1/docs/VALIDACAO.md).
