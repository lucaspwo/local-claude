# local-claude

Run [Claude Code](https://docs.anthropic.com/en/docs/claude-code) with local LLMs instead of the Anthropic API. Keeps the default `claude` command untouched — use `local-claude` when you want to go fully offline, offload inference to a remote GPU, or experiment with Apple Intelligence on-device.

## Why

Claude Code is an excellent coding agent, but it requires an Anthropic API subscription. This wrapper redirects it to a local or remote inference server (LM Studio, llama.cpp, a remote llama.cpp via SSH, or Apple Intelligence via [apfel](https://github.com/Arthur-Ficial/apfel)) so you can experiment with open-weight models at zero cost.

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
  - [apfel](https://github.com/Arthur-Ficial/apfel) for Apple Intelligence (macOS 26+, Apple Silicon)

## Install

```bash
# Clone
git clone https://github.com/lucaspwo/local-claude.git
cd local-claude

# Copy scripts to PATH
cp local-claude apfel-proxy.py ~/.local/bin/
chmod +x ~/.local/bin/local-claude
```

## Project structure

```
local-claude     Bash wrapper — entry point, backend detection/selection, launches `claude`
apfel-proxy.py   Anthropic ↔ OpenAI translation proxy, used only by the `apfel` backend
README.md        This file
MANUTENCAO.md    Deep maintenance guide (Portuguese)
AGENTS.md        Symbol map and conventions for LLM agents
CLAUDE.md        Claude-Code-specific notes (Portuguese)
LICENSE          MIT
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

### With Apple Intelligence (macOS 26+)

Uses Apple's on-device foundation model via [apfel](https://github.com/Arthur-Ficial/apfel). Requires Apple Silicon, macOS 26 Tahoe, and Apple Intelligence enabled.

```bash
brew tap Arthur-Ficial/tap && brew install apfel
local-claude --backend apfel
```

> **Important limitations:** Apple Intelligence has a **4096-token context window** — far too small for Claude Code's tool schemas and system prompt. The backend runs in **chat-only mode** (`--bare --tools ""`): you can have conversations, but the agent cannot use tools (edit files, run commands, etc.). A lightweight proxy (`apfel-proxy.py`) translates between the Anthropic Messages API that Claude Code speaks and the OpenAI Chat Completions API that apfel exposes.

### With a pre-running remote server

If you prefer to manage the remote server yourself, use the `remote` backend to connect to any already-running OpenAI-compatible server:

```bash
local-claude --backend remote --host 192.0.2.100 --port 8091
```

### Shell aliases (optional)

```bash
# ~/.zshrc or ~/.bashrc
alias sl='local-claude'                                # LM Studio
alias sllama='local-claude --backend llama'            # llama.cpp (local)
alias sremote='local-claude --backend remote-llama'    # llama.cpp (remote via SSH)
alias sapfel='local-claude --backend apfel'            # Apple Intelligence

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
| `apfel` | Starts apfel + API proxy | Apple Intelligence on-device (chat only) |

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
| `APFEL_PORT` | `11434` | apfel server port |
| `APFEL_ARGS` | — | Extra arguments for `apfel --serve` (e.g., `--cors --max-concurrent 5`) |
| `REMOTE_SSH_HOST` | *(required)* | SSH host for `remote-llama` backend |
| `REMOTE_MODELS_DIR` | *(required)* | Absolute path to GGUF directory on the remote host (e.g., `/home/<user>/models/gguf`) |
| `REMOTE_LLAMA_DIR` | *(required)* | Absolute path to llama-server directory on the remote host (e.g., `/home/<user>/git/llama.cpp/build/bin`) |
| `REMOTE_LLAMA_TQ3_DIR` | *(required with `--tq3`)* | Absolute path to llama-server directory for the TQ3 fork (e.g., `/home/<user>/git/llama.cpp-tq3/build/bin`) |
| `LLAMA_CTX_SIZE` | `65536` (or `32768` with `--tq3`) | Context size for `llama` and `remote-llama` backends |

### Examples

```bash
# Use a remote LM Studio server
local-claude --host 192.0.2.62

# Use a specific draft model
LLAMA_DRAFT=~/Models/gguf/qwen2.5-0.5b-instruct-q8_0.gguf local-claude --backend llama

# Remote llama.cpp via SSH (all 4 vars are required)
REMOTE_SSH_HOST=myserver \
REMOTE_MODELS_DIR=/home/lucas/models/gguf \
REMOTE_LLAMA_DIR=/home/lucas/git/llama.cpp/build/bin \
LCC_HOST=192.0.2.5 \
local-claude --backend remote-llama

# Connect to a pre-running remote server
local-claude --backend remote --host 192.0.2.5 --port 8091
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
- `llama-server` binary (Linux) on the remote host
- GGUF model files in `REMOTE_MODELS_DIR` on the remote host (use absolute paths — `~` is not expanded over SSH)
- The remote server listens on `0.0.0.0` so it's accessible from the network

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
| apfel "context_length_exceeded" | Apple Intelligence has a hard 4096-token limit. The backend already uses `--bare --tools ""` to minimize context. Keep messages short |
| apfel proxy connection refused | The apfel server crashed (known issue with FoundationModels framework). Restart with `local-claude --backend apfel` |
| apfel "model does not exist" | The proxy should rewrite all model names. Check `/tmp/apfel-proxy.log` for details |
| Model too slow | Use a smaller quantization or smaller model. 7B Q8_0 + 0.5B draft is a good sweet spot |
| CUDA not loading on remote host | Run `nvidia-smi` over SSH. If it fails, the NVIDIA driver isn't installed or the user can't access it. Prebuilt llama.cpp Linux binaries bundle the CUDA runtime — only the driver is required |

## Setting up a remote Ubuntu Server host with NVIDIA GPU

Complete step-by-step guide to set up an Ubuntu Server PC as a remote llama.cpp inference server. This was tested with an NVIDIA RTX 4070 Ti SUPER (16 GB VRAM) and Qwen2.5 models.

### 1. Enable SSH access

Ubuntu Server ships with `openssh-server` enabled by default. If not:

```bash
sudo apt update && sudo apt install -y openssh-server
sudo systemctl enable --now ssh
```

On the client machine, add an entry to `~/.ssh/config`:

```
Host my-remote-pc
  HostName <IP or Tailscale address>
  User <username>
  IdentityFile ~/.ssh/id_ed25519
```

Test: `ssh my-remote-pc "uname -a"` — should show a Linux kernel.

### 2. Install the NVIDIA driver and CUDA toolkit

llama.cpp publishes no prebuilt Ubuntu+CUDA binary, so we need both the driver *and* the CUDA toolkit (used at build time).

```bash
# Driver — pick the recommended one for the GPU
sudo ubuntu-drivers install
# Or pin a specific version (CUDA 13.x needs driver ≥ 580; CUDA 12.x needs ≥ 545):
sudo apt install -y nvidia-driver-580

sudo reboot
```

After reboot, verify the driver:

```bash
nvidia-smi
# Should show the GPU model and driver version
```

Install the CUDA toolkit. Easiest path is NVIDIA's apt repo (more recent than `nvidia-cuda-toolkit` from Ubuntu's archive):

```bash
# https://developer.nvidia.com/cuda-downloads — pick "deb (network)" for your Ubuntu version
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install -y cuda-toolkit   # Pulls the latest available (13.x at time of writing)

# Add to PATH (in ~/.bashrc):
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

nvcc --version   # Verify
```

### 3. Build llama.cpp with CUDA support

```bash
sudo apt install -y build-essential cmake git

# Use absolute paths — ~ is not expanded over SSH
mkdir -p "$HOME/git"
git clone https://github.com/ggml-org/llama.cpp.git "$HOME/git/llama.cpp"
cd "$HOME/git/llama.cpp"

cmake -B build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j "$(nproc)"

# The binary lands in build/bin/
ls -lh build/bin/llama-server
```

Verify CUDA is wired in:

```bash
"$HOME/git/llama.cpp/build/bin/llama-server" --help 2>&1 | head -5
# Should show: "ggml_cuda_init: found 1 CUDA devices"
# If it only shows "load_backend: loaded CPU backend", CUDA wasn't detected at build time
```

Set `REMOTE_LLAMA_DIR` to `/home/<user>/git/llama.cpp/build/bin` (where `llama-server` lives).

Create the models directory:

```bash
mkdir -p "$HOME/models/gguf"   # Or use a larger drive, e.g., /data/models/gguf
```

> **Optional — TQ3 fork.** If you also want the [TQ3 quantization fork](https://github.com/turbo-tan/llama.cpp-tq3) (used by `local-claude --backend remote-llama --tq3`), clone and build it side-by-side as `$HOME/git/llama.cpp-tq3`, then set `REMOTE_LLAMA_TQ3_DIR` to its `build/bin` directory.

### 4. Download GGUF models

Download models from [Hugging Face](https://huggingface.co/models?search=gguf). For Qwen2.5 with speculative decoding:

```bash
MODELS="$HOME/models/gguf"   # Adjust to your storage path

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

> **Tip:** Keep llama.cpp binaries on a fast SSD, but models can live on a slower drive — they're read sequentially into VRAM at startup and not accessed from disk again.

### 5. Configure the client

On your local machine (the one running Claude Code), set the environment variables. Best done in your shell profile:

```bash
# ~/.zshrc or ~/.bashrc
export REMOTE_SSH_HOST="my-remote-pc"                            # SSH config host name
export REMOTE_MODELS_DIR="/home/lucas/models/gguf"               # absolute path on the remote host
export REMOTE_LLAMA_DIR="/home/lucas/git/llama.cpp/build/bin"    # absolute path on the remote host
export LCC_HOST="192.0.2.5"                                      # IP of remote host (reachable from client)
```

Then run:

```bash
local-claude --backend remote-llama
```

### 6. Gotchas we discovered

- **Use absolute paths in `REMOTE_MODELS_DIR` / `REMOTE_LLAMA_DIR`.** The script passes these values inside single quotes over SSH, so `~` is **not expanded** on the remote side. Use `/home/<user>/...` (or wherever the data lives).
- **Port 8090 collisions are rare on Ubuntu Server**, but the script still defaults to **8091**. If that's taken, set `LCC_PORT` to another value.
- **CUDA toolkit is NOT required.** The prebuilt Linux binaries include the CUDA runtime. Only the NVIDIA display driver must be installed.
- **Disk space:** Check free space before downloading models. A full disk causes `curl: (23) Failure writing output to destination` errors without clear explanation.
- **Split GGUF files:** Some models (7B Q8_0, 14B Q4_K_M) are split into multiple files on Hugging Face. Download **all** parts. The script auto-detects them and only shows the model name once in the selection menu.
- **Firewall:** if `ufw` is enabled, allow the port: `sudo ufw allow 8091/tcp`.

### VRAM sizing guide

| Model | Quantization | VRAM (approx) | Quality | Fits 8 GB | Fits 16 GB | Fits 24 GB |
|---|---|---|---|---|---|---|
| 0.5B | Q8_0 | ~0.7 GB | Draft only | ✅ | ✅ | ✅ |
| 3B | Q4_K_M | ~2.5 GB | Basic | ✅ | ✅ | ✅ |
| 7B | Q8_0 | ~9.3 GB | Good | ❌ | ✅ | ✅ |
| 14B | Q4_K_M | ~10 GB | Better | ❌ | ✅ | ✅ |
| 14B | Q8_0 | ~16 GB | Best 14B | ❌ | ⚠️ tight | ✅ |

> The draft model (0.5B) adds ~0.7 GB on top. With a 7B Q8_0 + 0.5B draft, total VRAM is ~10 GB.

## Related documentation

- [MANUTENCAO.md](MANUTENCAO.md) — maintenance guide, architecture, key symbols (Portuguese)
- [AGENTS.md](AGENTS.md) — file map, symbol index, commands for LLM agents
- [CLAUDE.md](CLAUDE.md) — Claude-Code-specific notes (Portuguese)

## Credits

Inspired by [this XDA article](https://www.xda-developers.com/wrote-script-run-claude-code-local-llm-skipping-cloud/) on running Claude Code with local LLMs.

## License

MIT
