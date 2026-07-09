# AGENTS — local-claude

Bash wrapper that runs [Claude Code](https://docs.anthropic.com/en/docs/claude-code) against local/remote LLM backends instead of the Anthropic API · Stack: Bash (`set -euo pipefail`), Python 3 (stdlib only).

## File map

| Path | Purpose |
|---|---|
| `local-claude` | Entry point (bash, 598 lines). Parses `--backend`/`--host`/`--port`/`--tq3`, starts/discovers the chosen inference server, exports `ANTHROPIC_BASE_URL`/`ANTHROPIC_API_KEY`/`CLAUDE_CONFIG_DIR`, launches `claude` |
| `apfel-proxy.py` | HTTP proxy (Python 3, 386 lines, stdlib only). Translates Anthropic Messages API (`/v1/messages`) ↔ OpenAI Chat Completions (`/v1/chat/completions`). Used **only** by the `apfel` backend |
| `README.md` | User docs: install, usage per backend, config vars, troubleshooting |
| `MANUTENCAO.md` | Deep maintenance guide, Portuguese |
| `CLAUDE.md` | Claude-Code-specific notes, Portuguese |
| `LICENSE` | MIT |
| `docs/superpowers/specs/`, `docs/superpowers/plans/` | Planning artifacts for an unrelated doc-tooling task — not shipped code, not a maintenance reference |

## Key symbols

### `local-claude` (bash)

- `local-claude:33` — `set -euo pipefail` — fail-fast for the whole script.
- `local-claude:40-44` — `--backend` flag parsing.
- `local-claude:46-61` — `--host`/`--port`/`--tq3` parsing.
- `local-claude:63-72` — `CTX_SIZE` resolution (`LLAMA_CTX_SIZE` env > `--tq3` default 32768 > default 65536).
- `local-claude:74-79` — `pick_from_tty()` — reads user choice from `/dev/tty` (works even with stdin piped).
- `local-claude:82-190` — `llama` backend block: lists `.gguf` files, detects draft model (`local-claude:122-151`), starts `llama-server` in background, registers cleanup `trap` (`local-claude:164`).
- `local-claude:192-231` — `lmstudio` backend block: queries a running LM Studio's `/v1/models`.
- `local-claude:234-441` — `remote-llama` backend block: lists remote GGUFs over SSH (`local-claude:247-248`), filters split-GGUF parts (`local-claude:256-264`) and TQ3 models (`local-claude:267-275`), detects remote draft model (`local-claude:316-347`), `start_remote_server()` (`local-claude:350-401`) with automatic retry-without-draft on failure (`local-claude:403-422`).
- `local-claude:443-481` — `remote` backend block: connects to an already-running server, no lifecycle management.
- `local-claude:484-575` — `apfel` backend block: starts `apfel --serve` (`local-claude:506-531`) and the Python proxy (`local-claude:535`), registers `trap cleanup_apfel EXIT` (`local-claude:547`), forces `--bare --tools ""` (`local-claude:572`) due to Apple Intelligence's 4096-token context limit.
- `local-claude:583-598` — final launch: exports `ANTHROPIC_BASE_URL`/`ANTHROPIC_API_KEY`/`CLAUDE_CONFIG_DIR`; runs `claude` as a subprocess (not `exec`) when a background process needs cleanup (`local-claude:593-595`), else `exec claude` directly (`local-claude:596-597`).

### `apfel-proxy.py` (Python)

- `apfel-proxy.py:19` — `anthropic_to_openai(body)` — Anthropic request → OpenAI request. Always forces `model = "apple-foundationmodel"` (`apfel-proxy.py:79-82`).
- `apfel-proxy.py:111` — `openai_to_anthropic(oai, model)` — OpenAI non-streaming response → Anthropic response.
- `apfel-proxy.py:156` — `openai_stream_to_anthropic_stream(oai_lines, model)` — OpenAI SSE stream → Anthropic SSE events.
- `apfel-proxy.py:264` — `class ProxyHandler(BaseHTTPRequestHandler)`.
- `apfel-proxy.py:275` / `apfel-proxy.py:282` — `do_GET`/`do_POST` routing (`/v1/models`, `/health`, `/v1/messages`, `/v1/messages/count_tokens`).
- `apfel-proxy.py:309` — `_handle_messages()` — main request handler, dispatches streaming vs non-streaming.
- `apfel-proxy.py:365` — `main()` — arg parsing (`--port`, `--upstream`, `--forward-tools`), starts `HTTPServer`.

## Commands

- Build: none
- Test: none
- Lint: none
- Run: `./local-claude` (default `lmstudio` backend), or `./local-claude --backend llama|remote|remote-llama|apfel [--host H] [--port P] [--tq3]`

## Conventions & constraints

- Bash: `set -euo pipefail` (`local-claude:33`) — every backend block must fail fast, not swallow errors.
- Every backend block in `local-claude` follows the same contract: set `BASE_URL` and `MODEL`, optionally set `EXTRA_CLAUDE_ARGS`, register an `EXIT` trap only if it started a background process.
- No config files anywhere — everything is env vars with the `"${VAR:-default}"` bash pattern (e.g. `local-claude:35-37`). Keep new config this way; don't introduce a config file format.
- `apfel-proxy.py` is stdlib-only (`http.server`, `urllib`, `json`, `argparse`) — do not add third-party dependencies without strong justification (no `requirements.txt`/`pyproject.toml` exists).
- Known bug: `--forward-tools` in `apfel-proxy.py` is dead code — `main()` (`apfel-proxy.py:365-374`) is missing `global forward_tools`, so the flag never reaches the module-level variable read at `apfel-proxy.py:95`. Fix by adding `global forward_tools` alongside `global upstream` at `apfel-proxy.py:366`.

## Common change recipes

1. **Add a new backend:** add an `elif [[ "$BACKEND" == "new" ]]; then ... fi` block in `local-claude` between lines 234 and 577, following the existing pattern. Set `BASE_URL`/`MODEL`; if it starts a background process, register a `trap ... EXIT` (see `local-claude:164` or `local-claude:539-547`) so cleanup runs on exit.
2. **Change default context size for `llama`/`remote-llama`:** edit `local-claude:63-72`, or set the `LLAMA_CTX_SIZE` env var (already supported, no code change needed).
3. **Change Anthropic↔OpenAI translation for `apfel`:** edit `anthropic_to_openai` (`apfel-proxy.py:19`) for requests, `openai_to_anthropic` (`apfel-proxy.py:111`) for non-streaming responses, `openai_stream_to_anthropic_stream` (`apfel-proxy.py:156`) for streaming.
4. **Add a new config env var:** document it in the "Configuration" table in `README.md` and follow the existing `"${VAR:-default}"` pattern.

## Do NOT touch

- `docs/superpowers/specs/`, `docs/superpowers/plans/` — planning artifacts for a separate documentation-tooling task, not part of this repo's shipped code.
- `.specstory/` — session-history directory, gitignored (`.gitignore:1`).
