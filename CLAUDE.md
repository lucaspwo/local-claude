# CLAUDE.md — local-claude

Wrapper bash que roda o Claude Code contra LLMs locais/remotos (LM Studio, llama.cpp, apfel/Apple Intelligence) em vez da API da Anthropic.

## Comandos essenciais

Não há build, teste ou lint no repo. Só há como rodar:

```bash
./local-claude                          # backend padrão: lmstudio
./local-claude --backend llama          # llama.cpp local
./local-claude --backend remote-llama   # llama.cpp remoto via SSH
./local-claude --backend apfel          # Apple Intelligence (macOS 26+)
```

Após editar o script, teste manualmente com o backend relevante — não há suite automatizada para validar a mudança.

## Gotchas (top)

- `local-claude:33` — `set -euo pipefail`: qualquer comando novo que falhe silenciosamente quebra o script inteiro. Trate erros explicitamente onde um `|| true` for intencional.
- Backends `llama`/`remote-llama`/`apfel` rodam `claude` como subprocesso (`local-claude:593-595`), não `exec` — precisam manter o bash vivo para o `trap ... EXIT` matar servidores em background. `lmstudio`/`remote` usam `exec claude` (`local-claude:596-597`) porque não gerenciam ciclo de vida de servidor. Ao adicionar um backend que sobe processo próprio, seguir o padrão do primeiro grupo.
- `apfel-proxy.py:366` tem um bug real: `main()` declara `global upstream` mas não `global forward_tools`, então `--forward-tools` na CLI nunca chega à variável de módulo lida em `apfel-proxy.py:95` — a flag é código morto. Ver `MANUTENCAO.md` para o fix.
- `REMOTE_MODELS_DIR`/`REMOTE_LLAMA_DIR`/`REMOTE_LLAMA_TQ3_DIR` precisam ser caminhos absolutos — `~` não é expandido sobre SSH (`local-claude:366-378`).
- Não editar `docs/superpowers/specs/` nem `docs/superpowers/plans/` — são specs/planos de uma tarefa de tooling de documentação, não código deste repo.

## Ponteiros

- Arquitetura e receitas de mudança → [MANUTENCAO.md](MANUTENCAO.md)
- Mapa de símbolos e comandos (para LLM/agente) → [AGENTS.md](AGENTS.md)

## Commit/push

O remote `origin` tem dois `pushurl` configurados: GitHub (`git@github.com:lucaspwo/local-claude.git`) e o GitLab do homelab (`ssh://git@gitlab.lab.lucaspwo.com:2222/lucaspwo/local-claude.git`). `git push` sem argumentos já envia para os dois. Se o homelab estiver inacessível (fora da Tailscale), o push para o GitHub ainda vai — re-tente o homelab depois.

Nunca usar `--no-verify`. Nunca fazer commit de código que não roda (`bash -n local-claude` / `python3 -m py_compile apfel-proxy.py` antes de commitar mudanças nesses arquivos).
