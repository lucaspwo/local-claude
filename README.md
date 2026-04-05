# local-claude

Run [Claude Code](https://docs.anthropic.com/en/docs/claude-code) with local LLMs instead of the Anthropic API. Keeps the default `claude` command untouched — use `local-claude` when you want to go fully offline.

## Why

Claude Code is an excellent coding agent, but it requires an Anthropic API subscription. This wrapper redirects it to a local inference server (LM Studio or llama.cpp) so you can experiment with open-weight models at zero cost.

The default `claude` command remains unchanged — your cloud subscription is never affected.

## How it works

```
local-claude  ──►  sets env vars  ──►  claude --model <detected-model>
                       │
                       ├── ANTHROPIC_BASE_URL → local server
                       ├── ANTHROPIC_API_KEY  → "local"
                       ├── CLAUDE_CONFIG_DIR  → ~/.claude-local (isolated)
                       └── CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC → 1
```

The script:
1. Queries the local server's `/v1/models` endpoint
2. Lets you pick a model (or auto-selects if only one is loaded)
3. For llama.cpp: auto-starts `llama-server` and kills it on exit
4. For llama.cpp: auto-detects the smallest same-family model for [speculative decoding](https://github.com/ggml-org/llama.cpp/blob/master/examples/speculative/README.md)
5. Launches `claude` with the right environment

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed (`claude` in PATH)
- Python 3 (for model selection logic)
- One of:
  - [LM Studio](https://lmstudio.ai/) with local server enabled
  - [llama.cpp](https://github.com/ggml-org/llama.cpp) built with `llama-server`

## Install

```bash
# Clone
git clone https://github.com/YOUR_USER/local-claude.git
cd local-claude

# Copy script to PATH
cp local-claude ~/.local/bin/
chmod +x ~/.local/bin/local-claude
```

## Usage

### With LM Studio (default)

Start LM Studio, load a model, enable the local server (port 1234), then:

```bash
local-claude
```

### With llama.cpp

Place `.gguf` files in `~/Models/gguf/` (or set `MODELS_DIR`), then:

```bash
local-claude --backend llama
```

The script starts `llama-server`, lets you pick a model, and **automatically stops the server when you exit Claude Code**.

### Shell aliases (optional)

```bash
# ~/.zshrc or ~/.bashrc
alias sl='local-claude'                          # LM Studio
alias sllama='local-claude --backend llama'      # llama.cpp

# With SpecStory session recording
alias slocal='specstory run claude -c local-claude --no-cloud-sync'
alias sllama='specstory run claude -c "local-claude --backend llama" --no-cloud-sync'
```

## Configuration

All settings are via environment variables — no config files needed.

| Variable | Default | Description |
|---|---|---|
| `LCC_HOST` | `127.0.0.1` | LM Studio server host |
| `LCC_PORT` | `1234` | LM Studio server port |
| `LLAMA_PORT` | `8090` | llama.cpp server port |
| `LLAMA_SERVER` | `~/git/llama.cpp/build/bin/llama-server` | Path to llama-server binary |
| `MODELS_DIR` | `~/Models/gguf` | Directory containing .gguf model files |
| `LLAMA_DRAFT` | *(auto-detected)* | Explicit path to draft model for speculative decoding |

### Examples

```bash
# Use a remote LM Studio server
LCC_HOST=192.168.0.62 local-claude

# Use a specific draft model
LLAMA_DRAFT=~/Models/gguf/qwen2.5-0.5b-instruct-q8_0.gguf local-claude --backend llama

# Change llama.cpp context size (edit the script or set before calling)
LLAMA_PORT=9090 local-claude --backend llama
```

## Speculative decoding

When using the llama.cpp backend, the script automatically enables [speculative decoding](https://github.com/ggml-org/llama.cpp/blob/master/examples/speculative/README.md) if it finds a smaller model from the same family in your models directory.

**How it works:** A small "draft" model generates candidate tokens that the larger "target" model verifies in a single batch. Accepted tokens are free — rejected ones get regenerated normally. The result is identical output at higher throughput.

**Example:** With Qwen2.5-7B as target and Qwen2.5-0.5B as draft on Apple M4 Pro (24 GB):

| Target | Draft | Tokens/sec | Speedup |
|---|---|---|---|
| 7B Q8_0 | *(none)* | 29 t/s | — |
| 7B Q8_0 | 0.5B Q8_0 | 57 t/s | ~2x |
| 7B Q8_0 | 1.5B Q4_K_M | 46 t/s | 1.6x |
| 7B Q8_0 | 3B Q4_K_M | 36 t/s | 1.2x |

**Key insight:** The smallest draft model wins. The 3B draft is slower than 1.5B despite higher acceptance rate — verification overhead dominates. The script picks the smallest by default.

To override auto-detection:

```bash
LLAMA_DRAFT=/path/to/draft.gguf local-claude --backend llama
```

## MCP servers

If you use [MCP servers](https://modelcontextprotocol.io/) with Claude Code and want them available in LM Studio too, add them to `~/.lmstudio/mcp.json`:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"]
    },
    "a11y-accessibility": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "a11y-mcp-server"]
    }
  }
}
```

> **Tip:** If `npx` isn't in LM Studio's PATH, use the full path (e.g., `~/.nvm/versions/node/v20.20.2/bin/npx`) and add a `PATH` entry in `env`.

## Architecture notes

### Config isolation

The script sets `CLAUDE_CONFIG_DIR=~/.claude-local` so the local session uses a separate config directory. This prevents conflicts with your cloud claude.ai login — `claude` and `local-claude` can coexist without auth errors.

### Server lifecycle (llama.cpp)

When using `--backend llama`, the script:
1. Starts `llama-server` as a background process
2. Registers a `trap EXIT` handler to kill it
3. Runs `claude` as a **subprocess** (not `exec`) so the trap survives
4. When Claude Code exits (`/exit`, Ctrl+C, etc.), the trap fires and stops the server

For LM Studio, the script uses `exec claude` since there's no server to manage.

### Context size

Claude Code's system prompt uses ~27K tokens. The script defaults to `--ctx-size 32768`. If you encounter "exceeds context size" errors, increase this value in the script. Larger context = more RAM usage.

## Troubleshooting

| Problem | Solution |
|---|---|
| "Auth conflict" error | The script should handle this. If not, run `claude /logout` in a separate terminal |
| "exceeds context size" | Model context too small. Edit `--ctx-size` in the script or use a larger value |
| llama-server won't start | Check `/tmp/llama-server.log` for details |
| Speculative decoding not activating | Ensure draft model is same family (e.g., both Qwen2.5). Check script output for "Draft model" line |
| LM Studio speculative decoding error | Disable it in LM Studio's model settings — it conflicts with MLX batched inference |
| Model too slow | Use a smaller quantization or smaller model. 7B Q8_0 + 0.5B draft is a good sweet spot for 24 GB RAM |

## Credits

Inspired by [this XDA article](https://www.xda-developers.com/wrote-script-run-claude-code-local-llm-skipping-cloud/) on running Claude Code with local LLMs.

## License

MIT
