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
4. For llama.cpp backends: auto-detects the smallest same-family model for [speculative decoding](https://github.com/ggml-org/llama.cpp/blob/master/examples/speculative/README.md) (with automatic fallback if the draft model is incompatible)
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
| `LCC_HOST` | — | Remote server host IP (used by `remote` and `remote-llama` backends only) |
| `LCC_PORT` | `8091` | Remote server port (`remote` and `remote-llama` backends) |
| `LLAMA_PORT` | `8090` | llama.cpp local server port |
| `LLAMA_SERVER` | `~/git/llama.cpp/build/bin/llama-server` | Path to llama-server binary |
| `MODELS_DIR` | `~/Models/gguf` | Directory containing .gguf model files |
| `LLAMA_DRAFT` | *(auto-detected)* | Explicit path to draft model for speculative decoding |
| `REMOTE_SSH_HOST` | *(required)* | SSH host for `remote-llama` backend |
| `REMOTE_MODELS_DIR` | *(required)* | GGUF directory on the remote host (WSL2 path, e.g., `/mnt/d/Models/gguf`) |
| `REMOTE_LLAMA_DIR` | *(required)* | llama-server directory on the remote host (WSL2 path, e.g., `/mnt/c/llama.cpp/bin`) |

### Examples

```bash
# Use a remote LM Studio server
local-claude --host 192.168.0.62

# Use a specific draft model
LLAMA_DRAFT=~/Models/gguf/qwen2.5-0.5b-instruct-q8_0.gguf local-claude --backend llama

# Remote llama.cpp via SSH (all 4 vars are required)
REMOTE_SSH_HOST=myserver \
REMOTE_MODELS_DIR=/mnt/d/Models/gguf \
REMOTE_LLAMA_DIR=/mnt/c/llama.cpp/bin \
LCC_HOST=10.0.0.5 \
local-claude --backend remote-llama

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

Claude Code's system prompt uses ~27K tokens. The script defaults to `--ctx-size 65536`. If you encounter "exceeds context size" errors, increase this value in the script. Larger context = more RAM/VRAM usage.

## Troubleshooting

| Problem | Solution |
|---|---|
| "Auth conflict" error | The script should handle this. If not, run `claude /logout` in a separate terminal |
| "exceeds context size" | Model context too small. Edit `--ctx-size` in the script or use a larger value |
| llama-server won't start | Check `/tmp/llama-server.log` for details (local or remote) |
| Remote server not responding | Check SSH connectivity, firewall rules, and that the port is not in use |
| Port already in use | Another service may be using the port. Try a different `LCC_PORT` |
| Speculative decoding not activating | Ensure draft model is same family (e.g., both Qwen2.5). Check script output for "Draft model" line |
| Draft model fails to load | Some model pairs are incompatible in certain llama.cpp versions (`invalid vector subscript`). The script retries without speculative decoding automatically |
| LM Studio speculative decoding error | Disable it in LM Studio's model settings — it conflicts with MLX batched inference |
| Model too slow | Use a smaller quantization or smaller model. 7B Q8_0 + 0.5B draft is a good sweet spot |
| CUDA not loading on remote Windows | Ensure CUDA runtime DLLs (`cudart64_*.dll`, `cublas64_*.dll`) are in the same directory as `llama-server.exe` |

## Setting up a remote Windows host with NVIDIA GPU

Complete step-by-step guide to set up a Windows PC as a remote llama.cpp inference server. This was tested with an NVIDIA RTX 4070 Ti SUPER (16 GB VRAM) and Qwen2.5 models.

### 1. Enable SSH access

The `remote-llama` backend SSHes into **WSL2** on the Windows host (not native Windows SSH), because it needs to run `llama-server.exe` from a Unix shell while passing Windows-style paths.

- Install WSL2 on the Windows host: `wsl --install` (from an admin PowerShell)
- Install an SSH server inside WSL2: `sudo apt install openssh-server`
- Start the SSH server: `sudo service ssh start`
- Configure it to listen on a different port (e.g., 2222) to avoid conflict with Windows' own SSH:
  ```bash
  # In WSL2: edit /etc/ssh/sshd_config, set Port 2222
  sudo service ssh restart
  ```
- On the client machine, add an entry to `~/.ssh/config`:
  ```
  Host my-remote-pc
    HostName <IP or Tailscale address>
    Port 2222
    User <wsl-username>
    IdentityFile ~/.ssh/id_ed25519
  ```
- Test: `ssh my-remote-pc "uname -a"` — should show a Linux kernel

### 2. Download llama.cpp (prebuilt, no compilation needed)

From the WSL2 shell on the remote host, or via SSH:

```bash
# Create directories
mkdir -p /mnt/c/llama.cpp/bin
mkdir -p /mnt/d/Models/gguf   # Use a drive with enough space

# Download latest release (check https://github.com/ggml-org/llama.cpp/releases)
VERSION="b8668"  # Replace with latest
cd /tmp

# Main binary (CUDA 12.4 — works with most modern NVIDIA drivers)
wget "https://github.com/ggml-org/llama.cpp/releases/latest/download/llama-${VERSION}-bin-win-cuda-12.4-x64.zip"

# CUDA runtime DLLs (required — not included in the main binary)
wget "https://github.com/ggml-org/llama.cpp/releases/latest/download/cudart-llama-bin-win-cuda-12.4-x64.zip"

# Extract BOTH to the SAME directory
cd /mnt/c/llama.cpp/bin
unzip /tmp/llama-${VERSION}-bin-win-cuda-12.4-x64.zip
unzip /tmp/cudart-llama-bin-win-cuda-12.4-x64.zip
```

> **Critical:** You must extract **both** zips to the same directory. The main binary contains `ggml-cuda.dll` but it depends on `cudart64_12.dll`, `cublas64_12.dll`, and `cublasLt64_12.dll` from the cudart zip. Without them, llama-server silently falls back to CPU-only inference.

Verify CUDA is detected:
```bash
cd /mnt/c/llama.cpp/bin
./llama-server.exe --help 2>&1 | head -5
# Should show: "ggml_cuda_init: found 1 CUDA devices"
# If it only shows "load_backend: loaded CPU backend", the CUDA DLLs are missing
```

### 3. Download GGUF models

Download models from [Hugging Face](https://huggingface.co/models?search=gguf). For Qwen2.5 with speculative decoding:

```bash
MODELS=/mnt/d/Models/gguf  # Adjust to your drive

# Main model — Qwen2.5-7B-Instruct Q8_0 (~8 GB, fits in 16 GB VRAM)
# Note: this model is split into 3 files, download ALL of them
for i in 1 2 3; do
  curl -L -o "$MODELS/qwen2.5-7b-instruct-q8_0-0000${i}-of-00003.gguf" \
    "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q8_0-0000${i}-of-00003.gguf"
done

# Draft model — Qwen2.5-0.5B-Instruct Q8_0 (~645 MB, for speculative decoding)
curl -L -o "$MODELS/qwen2.5-0.5b-instruct-q8_0.gguf" \
  "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q8_0.gguf"

# Optional: other sizes
# 3B Q4_K_M (~2 GB) — fast, lower quality
curl -L -o "$MODELS/qwen2.5-3b-instruct-q4_k_m.gguf" \
  "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf"

# 14B Q4_K_M (~9 GB, split) — better quality, tight fit in 16 GB VRAM
for i in 1 2 3; do
  curl -L -o "$MODELS/qwen2.5-14b-instruct-q4_k_m-0000${i}-of-00003.gguf" \
    "https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF/resolve/main/qwen2.5-14b-instruct-q4_k_m-0000${i}-of-00003.gguf"
done
```

> **Tip:** Keep llama.cpp binaries on the fastest SSD (for DLL loading), but models can live on a slower drive — they're read sequentially into VRAM at startup and not accessed from disk again.

### 4. Configure the client

On your local machine (the one running Claude Code), set the environment variables. Best done in your shell profile:

```bash
# ~/.zshrc or ~/.bashrc
export REMOTE_SSH_HOST="my-remote-pc"               # SSH config host name
export REMOTE_MODELS_DIR="/mnt/d/Models/gguf"        # WSL2 path to models on remote
export REMOTE_LLAMA_DIR="/mnt/c/llama.cpp/bin"       # WSL2 path to llama-server on remote
export LCC_HOST="10.0.0.5"                           # IP of remote host (reachable from client)
```

Then run:
```bash
local-claude --backend remote-llama
```

### 5. Gotchas we discovered

- **Port 8090 may be in use** by Windows services (`svchost.exe`). The script defaults to **8091** to avoid this. If that's also taken, set `LCC_PORT` to another value.
- **CUDA toolkit is NOT required.** The prebuilt binaries include everything needed. Only the NVIDIA display driver must be installed on the Windows host.
- **WSL2 paths vs Windows paths:** The script converts automatically (e.g., `/mnt/d/Models/...` → `D:\Models\...`). You always use WSL2 paths in the env vars.
- **Disk space:** Check free space before downloading models. A full C: drive causes `curl: (23) Failure writing output to destination` errors without clear explanation.
- **Split GGUF files:** Some models (7B Q8_0, 14B Q4_K_M) are split into multiple files on Hugging Face. Download **all** parts. The script auto-detects them and only shows the model name once in the selection menu.
- **Firewall:** Windows Firewall may block incoming connections to `llama-server.exe`. Allow it when prompted, or add a firewall rule for the port.

### VRAM sizing guide

| Model | Quantization | VRAM (approx) | Quality | Fits 8 GB | Fits 16 GB | Fits 24 GB |
|---|---|---|---|---|---|---|
| 0.5B | Q8_0 | ~0.7 GB | Draft only | ✅ | ✅ | ✅ |
| 3B | Q4_K_M | ~2.5 GB | Basic | ✅ | ✅ | ✅ |
| 7B | Q8_0 | ~9.3 GB | Good | ❌ | ✅ | ✅ |
| 14B | Q4_K_M | ~10 GB | Better | ❌ | ✅ | ✅ |
| 14B | Q8_0 | ~16 GB | Best 14B | ❌ | ⚠️ tight | ✅ |

> The draft model (0.5B) adds ~0.7 GB on top. With a 7B Q8_0 + 0.5B draft, total VRAM is ~10 GB.

## Credits

Inspired by [this XDA article](https://www.xda-developers.com/wrote-script-run-claude-code-local-llm-skipping-cloud/) on running Claude Code with local LLMs.

## License

MIT
