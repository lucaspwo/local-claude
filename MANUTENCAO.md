# Manutenção — local-claude

## Arquitetura

O repo tem dois artefatos de código independentes:

1. **`local-claude`** — script bash (598 linhas), ponto de entrada único. Detecta/inicia o backend de inferência escolhido (`--backend lmstudio|llama|remote|remote-llama|apfel`), descobre o modelo carregado, e lança `claude` (o binário do Claude Code) com `ANTHROPIC_BASE_URL`/`ANTHROPIC_API_KEY`/`CLAUDE_CONFIG_DIR` apontando para esse backend. O comando `claude` padrão nunca é alterado — o script só afeta o processo filho que ele mesmo lança.
2. **`apfel-proxy.py`** — proxy HTTP (386 linhas, só stdlib). Usado **apenas** pelo backend `apfel`: traduz `/v1/messages` (Anthropic Messages API, o que o Claude Code fala) para `/v1/chat/completions` (OpenAI Chat Completions, o que o [apfel](https://github.com/Arthur-Ficial/apfel)/Apple Intelligence expõe) e vice-versa, incluindo streaming SSE.

Para os backends `lmstudio`, `llama` e `remote-llama`, o script aponta `ANTHROPIC_BASE_URL` **direto** para o servidor (LM Studio / `llama-server`) — não há proxy Python no caminho. Só `apfel` precisa do proxy porque `apfel --serve` fala OpenAI, não Anthropic.

## Mapa de módulos/pastas

| Caminho | Responsabilidade |
|---|---|
| `local-claude` | Wrapper bash: parsing de flags, seleção de backend, gerenciamento de ciclo de vida de servidores locais/remotos, lançamento do `claude` |
| `apfel-proxy.py` | Proxy Anthropic↔OpenAI, usado só pelo backend `apfel` |
| `README.md` | Documentação de usuário (instalação, uso, troubleshooting) |
| `LICENSE` | MIT |
| `docs/superpowers/specs/`, `docs/superpowers/plans/` | Specs/planos de uma tarefa de tooling de documentação (não são código do repo — **não mexer, não são referência de manutenção**) |

## Onde ficam as funções-chave

### `local-claude` (bash)

- `local-claude:33` — `set -euo pipefail` — fail-fast em todo o script.
- `local-claude:40-44` — parsing de `--backend`.
- `local-claude:46-61` — parsing de `--host`, `--port`, `--tq3`.
- `local-claude:63-72` — cálculo de `CTX_SIZE` (env `LLAMA_CTX_SIZE` > `--tq3` (32768) > default 65536).
- `local-claude:74-79` — `pick_from_tty()` — lê escolha do usuário via `/dev/tty` (funciona mesmo com stdin redirecionado, ex.: sob `specstory run`).
- `local-claude:82-190` — bloco do backend `llama` (local): lista `.gguf` em `MODELS_DIR`, detecta modelo draft (`local-claude:122-151`), sobe `llama-server` em background e registra `trap` de kill no exit (`local-claude:164`).
- `local-claude:192-231` — bloco do backend `lmstudio`: consulta `/v1/models` do LM Studio já rodando.
- `local-claude:234-441` — bloco do backend `remote-llama`: lista GGUFs remotos via SSH (`local-claude:247-248`), filtra split-GGUF (`local-claude:256-264`) e modelos TQ3 (`local-claude:267-275`), detecta draft remoto (`local-claude:316-347`), sobe o servidor remoto via `start_remote_server()` (`local-claude:350-401`) com retry automático sem draft se falhar (`local-claude:403-422`).
- `local-claude:443-481` — bloco do backend `remote` (servidor já rodando, sem gerenciamento de ciclo de vida).
- `local-claude:484-575` — bloco do backend `apfel`: sobe `apfel --serve` (`local-claude:506-531`) e o proxy Python (`local-claude:535`), define `trap cleanup_apfel EXIT` (`local-claude:547`) para matar os dois processos, força `--bare --tools ""` (`local-claude:572`) por causa do limite de 4096 tokens do Apple Intelligence.
- `local-claude:583-598` — lançamento final: exporta `ANTHROPIC_BASE_URL`/`ANTHROPIC_API_KEY`/`CLAUDE_CONFIG_DIR`; roda `claude` como subprocesso (não `exec`) quando há processo em background a limpar (`local-claude:593-595`), ou `exec claude` direto quando não há (`local-claude:596-597`).

### `apfel-proxy.py`

- `apfel-proxy.py:19` — `anthropic_to_openai(body)` — converte request Anthropic → OpenAI ChatCompletions. Sempre força `model = "apple-foundationmodel"` (`apfel-proxy.py:79-82`), ignorando o modelo pedido pelo Claude Code.
- `apfel-proxy.py:95-106` — só inclui `tools` no request de saída se `forward_tools` for `True` (ver gotcha de bug abaixo).
- `apfel-proxy.py:111` — `openai_to_anthropic(oai, model)` — converte resposta não-streaming OpenAI → Anthropic.
- `apfel-proxy.py:156` — `openai_stream_to_anthropic_stream(oai_lines, model)` — converte stream SSE OpenAI → eventos SSE Anthropic (`message_start`, `content_block_*`, `message_delta`, `message_stop`).
- `apfel-proxy.py:264` — `class ProxyHandler(BaseHTTPRequestHandler)` — handler HTTP.
- `apfel-proxy.py:275-289` — `do_GET`/`do_POST` — roteamento: `GET /v1/models`, `/health` (forward direto); `POST /v1/messages`, `/v1/messages/count_tokens`.
- `apfel-proxy.py:309` — `_handle_messages()` — handler principal: converte request, chama upstream, converte resposta (streaming ou não).
- `apfel-proxy.py:365` — `main()` — parse de args (`--port`, `--upstream`, `--forward-tools`) e start do `HTTPServer`.

## Fluxos de dados

**Backends `lmstudio`/`llama`/`remote-llama`/`remote`:** `claude` → `ANTHROPIC_BASE_URL` (servidor OpenAI-compatible, direto) → resposta direto ao `claude`. Sem tradução de protocolo no caminho.

**Backend `apfel`:** `claude` → `POST /v1/messages` no proxy (`apfel-proxy.py:309`) → `anthropic_to_openai` (`apfel-proxy.py:19`) → `POST /v1/chat/completions` no `apfel --serve` (upstream `127.0.0.1:11434`) → resposta OpenAI → `openai_to_anthropic` ou `openai_stream_to_anthropic_stream` → resposta Anthropic de volta ao `claude`.

## Receitas de mudança comuns

1. **Adicionar um novo backend:** criar bloco `elif [[ "$BACKEND" == "novo" ]]; then ... fi` em `local-claude` entre as linhas 234 e 577 (mesmo padrão dos existentes); definir `BASE_URL` e `MODEL`; se subir processo em background, registrar `trap ... EXIT` (ver padrão em `local-claude:164` ou `local-claude:539-547`) para que o cleanup rode.
2. **Mudar o contexto padrão de `llama`/`remote-llama`:** editar a lógica em `local-claude:63-72`, ou preferencialmente setar a env `LLAMA_CTX_SIZE` (já suportada, sem editar código).
3. **Ajustar a tradução Anthropic↔OpenAI do backend `apfel`:** editar `anthropic_to_openai` (`apfel-proxy.py:19`) para o request; `openai_to_anthropic` (`apfel-proxy.py:111`) para resposta não-streaming; `openai_stream_to_anthropic_stream` (`apfel-proxy.py:156`) para streaming.
4. **Adicionar uma nova env var de configuração:** documentar na tabela "Configuration" do `README.md` e usar o padrão `"${VAR:-default}"` já usado em todo o `local-claude` (ex.: `local-claude:35-37`).

## Build / Test / Lint / Deploy

Não há build, testes, lint nem CI configurados no repo (nenhum `Makefile`, `pytest`, config de lint, ou workflow encontrado). "Deploy" é manual, conforme `README.md`:

```bash
cp local-claude apfel-proxy.py ~/.local/bin/
chmod +x ~/.local/bin/local-claude
```

## Gotchas e decisões de design

- **Bug conhecido: `--forward-tools` não funciona.** Em `apfel-proxy.py:366`, `main()` declara `global upstream` mas **não** `global forward_tools`. A atribuição em `apfel-proxy.py:374` (`forward_tools = args.forward_tools`) cria uma variável local à função, sem efeito sobre o `forward_tools` de nível de módulo (`apfel-proxy.py:16`, sempre `False`). Resultado: passar `--forward-tools` na CLI não habilita o encaminhamento de tool schemas em `anthropic_to_openai` (`apfel-proxy.py:95`) — o código morto passa despercebido porque o comportamento padrão (não encaminhar) é o desejado na prática (contexto de 4096 tokens do Apple Intelligence). Para corrigir: adicionar `global forward_tools` na linha 366.
- **`exec` vs subprocesso em `local-claude`:** os backends `llama`, `remote-llama` e `apfel` rodam `claude` como subprocesso (`local-claude:595`) em vez de `exec` (`local-claude:597`), porque precisam manter o bash vivo para o `trap ... EXIT` matar o servidor em background quando o Claude Code sai. `lmstudio` e `remote` usam `exec claude` direto pois não gerenciam ciclo de vida de servidor algum.
- **Isolamento de config:** `CLAUDE_CONFIG_DIR=~/.claude-local` (`local-claude:590`) evita conflito com o login `claude.ai` da conta cloud — permite `claude` e `local-claude` coexistirem sem erro de auth.
- **Caminhos absolutos obrigatórios em SSH:** `REMOTE_MODELS_DIR`/`REMOTE_LLAMA_DIR`/`REMOTE_LLAMA_TQ3_DIR` precisam ser absolutos — o script passa esses valores entre aspas simples sobre SSH (`local-claude:366-378`), então `~` não é expandido no lado remoto.
- **Retry automático sem draft model:** `start_remote_server()` (`local-claude:350`) é chamado primeiro com args de speculative decoding; se falhar, `local-claude:403-422` tenta de novo sem draft — alguns pares de modelo são incompatíveis em certas versões do llama.cpp (`invalid vector subscript`).
- **`apfel-proxy.py` sempre força o nome do modelo** para `"apple-foundationmodel"` (`apfel-proxy.py:81`), independente do que o Claude Code pediu (ex.: `claude-haiku` para tarefas internas) — o `apfel` rejeitaria outros nomes.

## Dependências e integrações

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (`claude` no PATH) — obrigatório.
- Python 3 — usado tanto pelo `local-claude` (seleção de modelo, parsing JSON) quanto pelo `apfel-proxy.py` (stdlib só: `http.server`, `urllib`, `json`, `argparse`).
- Um dos backends de inferência: [LM Studio](https://lmstudio.ai/), [llama.cpp](https://github.com/ggml-org/llama.cpp) (`llama-server`), host remoto com llama.cpp via SSH, ou [apfel](https://github.com/Arthur-Ficial/apfel) (Apple Intelligence, macOS 26+, Apple Silicon).
- `curl` e `ssh` — usados pelo `local-claude` para health-check de servidores e gerenciamento remoto.
