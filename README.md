# local-claude

Run [Claude Code](https://docs.anthropic.com/en/docs/claude-code) with local LLMs instead of the Anthropic API. Keeps the default `claude` command untouched — use `local-claude` when you want to go fully offline, or offload inference to a remote GPU.

## Why

Claude Code is an excellent coding agent, but it requires an Anthropic API subscription. This wrapper redirects it to a local or remote inference server (LM Studio, llama.cpp, or a remote llama.cpp via SSH) so you can experiment with open-weight models at zero cost.

The default `claude` command remains unchanged — your cloud subscription is never affected.

## How it works

```
local-claude  ──►  sets env vars  ──►  claude --model <detected-model>
                       │
                       ├── ANTHROPIC_BASE_URL → local/remote server
                       ├── ANTHROPIC_API_KEY  → "local"
                       ├── CLAUDE_CONFIG_DIR  → ~/.claude-local (isolated)
                       └── CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC → 1
```

The script:
1. Queries the server's `/v1/models` endpoint (or lists remote GGUF files via SSH)
2. Lets you pick a model (or auto-selects if only one is loaded)
3. For llama.cpp backends: auto-starts `llama-server` (locally or via SSH) and kills it on exit
4. For llama.cpp backends: auto-detects the smallest same-family model for [speculative decoding](https://github.com/ggml-org/llama.cpp/blob/master/examples/speculative/README.md)
5. Launches `claude` with the right environment

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed (`claude` in PATH)
- Python 3 (for model selection logic)
- One of:
  - [LM Studio](https://lmstudio.ai/) with local server enabled
  - [llama.cpp](https://github.com/ggml-org/llama.cpp) built with `llama-server`
  - A remote machine with llama.cpp and SSH access (for `remote-llama` backend)

## Install

```bash
# Clone
git clone https://github.com/lucaspwo/local-claude.git
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

### With llama.cpp (local)

Place `.gguf` files in `~/Models/gguf/` (or set `MODELS_DIR`), then:

```bash
local-claude --backend llama
```

The script starts `llama-server`, lets you pick a model, and **automatically stops the server when you exit Claude Code**.

### With remote llama.cpp (via SSH)

Offload inference to a remote machine (e.g., a desktop with a dedicated GPU). The script SSHs into the remote host, lists available GGUF models, starts `llama-server` there, and stops it when you exit:

```bash
local-claude --backend remote-llama
```

This is ideal for using a lightweight laptop (e.g., MacBook) as a client while a more powerful machine (e.g., a PC with an NVIDIA RTX GPU) handles inference.

### With a pre-running remote server

If you prefer to manage the remote server yourself, use the `remote` backend to connect to any already-running OpenAI-compatible server:

```bash
local-claude --backend remote --host 192.168.1.100 --port 8091
```

### Shell aliases (optional)

```bash
# ~/.zshrc or ~/.bashrc
alias sl='local-claude'                                # LM Studio
alias sllama='local-claude --backend llama'            # llama.cpp (local)
alias sremote='local-claude --backend remote-llama'    # llama.cpp (remote via SSH)

# With SpecStory session recording
alias slocal='specstory run claude -c local-claude --no-cloud-sync'
alias sllama='specstory run claude -c "local-claude --backend llama" --no-cloud-sync'
alias sremote='specstory run claude -c "local-claude --backend remote-llama" --no-cloud-sync'
```

## Backends

| Backend | Server management | Use case |
|---|---|---|
| `lmstudio` (default) | Connects to running LM Studio | GUI-based model management |
| `llama` | Starts/stops local `llama-server` | Local inference with llama.cpp |
| `remote-llama` | Starts/stops `llama-server` on remote host via SSH | Offload to a remote GPU |
| `remote` | Connects to any running server | Manual server management |

## Configuration

All settings are via environment variables — no config files needed.

| Variable | Default | Description |
|---|---|---|
| `LCC_HOST` | `127.0.0.1` | Server host (used by `lmstudio`, `remote`, `remote-llama`) |
| `LCC_PORT` | `1234` | Server port (`lmstudio` default; `remote`/`remote-llama` default: `8091`) |
| `LLAMA_PORT` | `8090` | llama.cpp local server port |
| `LLAMA_SERVER` | `~/git/llama.cpp/build/bin/llama-server` | Path to llama-server binary |
| `MODELS_DIR` | `~/Models/gguf` | Directory containing .gguf model files |
| `LLAMA_DRAFT` | *(auto-detected)* | Explicit path to draft model for speculative decoding |
| `REMOTE_SSH_HOST` | `Ancalagon_WSL2-Tailnet` | SSH host for `remote-llama` backend |
| `REMOTE_MODELS_DIR` | `/mnt/e/Models/gguf` | GGUF directory on the remote host (WSL2 path) |

### Examples

```bash
# Use a remote LM Studio server
LCC_HOST=192.168.0.62 local-claude

# Use a specific draft model
LLAMA_DRAFT=~/Models/gguf/qwen2.5-0.5b-instruct-q8_0.gguf local-claude --backend llama

# Remote llama.cpp with custom SSH host
REMOTE_SSH_HOST=myserver local-claude --backend remote-llama

# Connect to a pre-running remote server
local-claude --backend remote --host 10.0.0.5 --port 8091
```

## Speculative decoding

When using the `llama` or `remote-llama` backends, the script automatically enables [speculative decoding](https://github.com/ggml-org/llama.cpp/blob/master/examples/speculative/README.md) if it finds a smaller model from the same family in the models directory.

**How it works:** A small "draft" model generates candidate tokens that the larger "target" model verifies in a single batch. Accepted tokens are free — rejected ones get regenerated normally. The result is identical output at higher throughput.

**Example:** With Qwen2.5-7B as target and Qwen2.5-0.5B as draft:

| Target | Draft | Platform | Tokens/sec | Speedup |
|---|---|---|---|---|
| 7B Q8_0 | *(none)* | Apple M4 Pro (24 GB) | 29 t/s | — |
| 7B Q8_0 | 0.5B Q8_0 | Apple M4 Pro (24 GB) | 57 t/s | ~2x |
| 7B Q8_0 | 0.5B Q8_0 | RTX 4070 Ti SUPER (16 GB) | 177 t/s | ~6x |
| 7B Q8_0 | 1.5B Q4_K_M | Apple M4 Pro (24 GB) | 46 t/s | 1.6x |
| 7B Q8_0 | 3B Q4_K_M | Apple M4 Pro (24 GB) | 36 t/s | 1.2x |

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

When using `--backend llama` or `--backend remote-llama`, the script:
1. Starts `llama-server` as a background process (locally or via SSH)
2. Registers a `trap EXIT` handler to kill it
3. Runs `claude` as a **subprocess** (not `exec`) so the trap survives
4. When Claude Code exits (`/exit`, Ctrl+C, etc.), the trap fires and stops the server

For `lmstudio` and `remote`, the script uses `exec claude` since there's no server lifecycle to manage.

### Remote llama.cpp setup

The `remote-llama` backend expects:
- SSH access to the remote host (configured in `~/.ssh/config` or via `REMOTE_SSH_HOST`)
- `llama-server` binary on the remote host
- GGUF model files in `REMOTE_MODELS_DIR` on the remote host
- The remote server listens on `0.0.0.0` so it's accessible from the network

For a Windows host with WSL2, the script SSHs into WSL2, runs `llama-server.exe` (the Windows binary) with Windows-style paths, and converts paths automatically.

### Split GGUF support

Large models (e.g., 14B+) are often split into multiple `.gguf` files. The script handles this transparently:
- Only shows the first part in model selection (e.g., `qwen2.5-14b-instruct-q4_k_m.gguf` instead of all 3 parts)
- Passes the first part to `llama-server`, which loads the remaining parts automatically
- Draft model detection skips non-first split parts

### Context size

Claude Code's system prompt uses ~27K tokens. The script defaults to `--ctx-size 32768`. If you encounter "exceeds context size" errors, increase this value in the script. Larger context = more RAM/VRAM usage.

## Troubleshooting

| Problem | Solution |
|---|---|
| "Auth conflict" error | The script should handle this. If not, run `claude /logout` in a separate terminal |
| "exceeds context size" | Model context too small. Edit `--ctx-size` in the script or use a larger value |
| llama-server won't start | Check `/tmp/llama-server.log` for details (local or remote) |
| Remote server not responding | Check SSH connectivity, firewall rules, and that the port is not in use |
| Port already in use | Another service may be using the port. Try a different `LCC_PORT` |
| Speculative decoding not activating | Ensure draft model is same family (e.g., both Qwen2.5). Check script output for "Draft model" line |
| LM Studio speculative decoding error | Disable it in LM Studio's model settings — it conflicts with MLX batched inference |
| Model too slow | Use a smaller quantization or smaller model. 7B Q8_0 + 0.5B draft is a good sweet spot |
| CUDA not loading on remote Windows | Ensure CUDA runtime DLLs (`cudart64_*.dll`, `cublas64_*.dll`) are in the same directory as `llama-server.exe` |

## Setting up a remote Windows host with NVIDIA GPU

Quick guide to set up a Windows PC as a remote llama.cpp server:

1. **Download llama.cpp** prebuilt binaries with CUDA from [releases](https://github.com/ggml-org/llama.cpp/releases):
   - `llama-<version>-bin-win-cuda-12.4-x64.zip` (main binary)
   - `cudart-llama-bin-win-cuda-12.4-x64.zip` (CUDA runtime)

2. **Extract both** to the same directory (e.g., `C:\Users\you\llama.cpp\bin\`)

3. **Download GGUF models** to a models directory (e.g., `C:\Users\you\Models\gguf\`)

4. **Enable SSH** on Windows (Settings → Optional Features → OpenSSH Server) or use WSL2

5. **Configure SSH** on your client machine (`~/.ssh/config`) and set `REMOTE_SSH_HOST`

6. **Run** `local-claude --backend remote-llama`

## Credits

Inspired by [this XDA article](https://www.xda-developers.com/wrote-script-run-claude-code-local-llm-skipping-cloud/) on running Claude Code with local LLMs.

## License

MIT
