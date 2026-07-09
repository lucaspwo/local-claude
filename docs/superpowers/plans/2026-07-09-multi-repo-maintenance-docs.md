# Documentação de manutenção multi-repo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar/atualizar 4 documentos padronizados (README, MANUTENCAO, AGENTS, CLAUDE) em 22 repositórios do Lucas para instruir humanos e LLMs locais sobre manutenção, mudanças e onde ficam as funções importantes.

**Architecture:** Um template canônico define os 4 esqueletos e as regras de qualidade. Dois repos-piloto são feitos e aprovados antes de escalar. O restante é produzido por subagents paralelos (1 por repo), com Claude fazendo spot-check de precisão e commit/push por repo.

**Tech Stack:** Markdown; `git` (`/opt/homebrew/bin/git`); `gh` para visibilidade; agentes `general-purpose`/`Explore` para fan-out.

## Global Constraints

- **Idioma README:** inglês só em `local-claude` e `ancalagon-llm` (PUBLIC); PT em todos os outros 20 (PRIVATE).
- **Idioma MANUTENCAO.md e CLAUDE.md:** PT em todos.
- **Idioma AGENTS.md:** inglês em todos.
- **Localização:** os 4 arquivos na **raiz** de cada repo.
- **Merge, não sobrescrever:** preservar conteúdo bom existente; reorganizar para o template; complementar lacunas.
- **Precisão verificável:** toda referência `arquivo:linha` e todo símbolo citado deve ser real. Inventar = rejeitar. Spot-check obrigatório antes do commit.
- **Commit/push:** um commit por repo com os 4 docs; `git push` (vai para todos os remotes via pushurls). Nos 5 sem remote: só commit local. **Nunca** `--no-verify`.
- **git binário:** usar `/opt/homebrew/bin/git` (o shell de escrita tem PATH mínimo).
- **Mensagem de commit:** terminar com as linhas `Co-Authored-By:` e `Claude-Session:` do CLAUDE.md global.

---

### Task 1: Template canônico + brief de subagent

**Files:**
- Create: `/private/tmp/claude-501/-Users-lucas-git/29ed098e-5875-4609-816e-d1e1aa02ac0e/scratchpad/doc-template.md`

**Interfaces:**
- Produces: o texto-modelo dos 4 docs (esqueletos com seções) e o prompt-brief reutilizável entregue a cada subagent no fan-out (Task 5).

- [ ] **Step 1: Escrever os 4 esqueletos**

Conteúdo do `doc-template.md` (esqueletos exatos):

```markdown
## README.md  (EN se público, senão PT)
# <nome-do-projeto>
<1 parágrafo: o quê e porquê>
## Stack / Requisitos
## Instalação
## Como rodar
## Estrutura de pastas
## Documentação relacionada
- MANUTENCAO.md — guia de manutenção
- AGENTS.md — instruções para agentes/LLM
- CLAUDE.md — notas para Claude Code
## Licença   (se houver LICENSE)

## MANUTENCAO.md  (PT)
# Manutenção — <nome>
## Arquitetura
## Mapa de módulos/pastas
## Onde ficam as funções-chave      (lista `caminho:linha` → o que faz)
## Fluxos de dados
## Receitas de mudança comuns        ("adicionar X", "corrigir Y")
## Build / Test / Lint / Deploy
## Gotchas e decisões de design
## Dependências e integrações

## AGENTS.md  (EN)
# AGENTS — <name>
One-liner + stack.
## File map            (path → purpose)
## Key symbols         (symbol → `path:line` → what it does)
## Commands            (build/test/lint/run, exact)
## Conventions & constraints
## Common change recipes  (imperative, step-by-step)
## Do NOT touch

## CLAUDE.md  (PT)
# CLAUDE.md — <nome>
<1 linha do projeto>
## Comandos essenciais
## Gotchas (top 3-5)
## Ponteiros
- Arquitetura → MANUTENCAO.md
- Mapa de símbolos → AGENTS.md
## Commit/push
<lembrar espelhamento multi-remote; nos sem-remote, só commit local>
```

- [ ] **Step 2: Escrever o brief de subagent no mesmo arquivo**

Prompt reutilizável (variáveis entre `<>` preenchidas por repo):

```
Você documenta o repo em <REPO_PATH>. Leia o código a fundo (comece por
entrypoints, config, README existente e arquivos maiores). Produza 4 arquivos
na RAIZ do repo seguindo os esqueletos abaixo: README.md (<IDIOMA_README>),
MANUTENCAO.md (PT), AGENTS.md (EN), CLAUDE.md (PT).
Regras: (1) MERGE com o conteúdo existente desses arquivos, não descarte;
(2) toda referência caminho:linha e todo símbolo citado DEVE ser real —
verifique antes de escrever; (3) para repos grandes, mapeie os pontos-chave
e declare o que ficou de fora (sem cap silencioso).
Retorne: os caminhos escritos + a lista de símbolos citados (símbolo → caminho:linha)
para spot-check + 1 parágrafo do que cobriu e do que ficou de fora.
<ESQUELETOS>
```

- [ ] **Step 3: Verificar o template**

Run: `grep -c '^## ' /private/tmp/claude-501/-Users-lucas-git/29ed098e-5875-4609-816e-d1e1aa02ac0e/scratchpad/doc-template.md`
Expected: contém as seções dos 4 docs (README, MANUTENCAO, AGENTS, CLAUDE) e o brief. Confirmar visualmente que os 4 esqueletos e o brief estão presentes.

---

### Task 2: Piloto A — `ocr-pipeline-local` (Claude direto, exercita merge)

**Files:**
- Create/Modify em `/Users/lucas/git/intellissis/ocr-pipeline-local/`: `README.md`, `MANUTENCAO.md`, `AGENTS.md`, `CLAUDE.md` (os 3 últimos já existem → merge).

**Interfaces:**
- Consumes: `doc-template.md` (Task 1).
- Produces: os 4 docs aprovados que servem de referência de qualidade para o fan-out.

- [ ] **Step 1: Ler o repo a fundo**

Run: `/opt/homebrew/bin/git -C /Users/lucas/git/intellissis/ocr-pipeline-local ls-files | head -80` e ler entrypoints Python (`*.py` principais), config, README/CLAUDE/AGENTS atuais.

- [ ] **Step 2: Redigir os 4 docs (README em PT — repo PRIVATE)**

Escrever os 4 arquivos seguindo o template; **merge** com CLAUDE.md/AGENTS.md/README.md existentes.

- [ ] **Step 3: Spot-check de precisão**

Para 3 símbolos citados no AGENTS.md/MANUTENCAO.md, confirmar que existem:
Run: `/opt/homebrew/bin/git -C /Users/lucas/git/intellissis/ocr-pipeline-local grep -n "<símbolo>"`
Expected: cada símbolo aparece no `caminho:linha` citado.

- [ ] **Step 4: Apresentar ao Lucas para aprovação**

Mostrar os 4 docs. **GATE:** aguardar aprovação antes de seguir.

---

### Task 3: Piloto B — `duckdns-update` (extremo mínimo)

**Files:**
- Create/Modify em `/Users/lucas/git/apps_smaug/duckdns-update/`: `README.md` (existe → merge), `MANUTENCAO.md`, `AGENTS.md`, `CLAUDE.md`.

**Interfaces:**
- Consumes: `doc-template.md`, feedback do Piloto A.

- [ ] **Step 1: Ler o repo** (shell script pequeno: `duckdns-update.sh`, `.conf.example`, timer/service).

- [ ] **Step 2: Redigir os 4 docs** (README em PT — PRIVATE). Escalar profundidade ao tamanho: docs curtos e diretos.

- [ ] **Step 3: Spot-check** dos comandos e caminhos citados.

- [ ] **Step 4: Apresentar ao Lucas.** **GATE:** aguardar aprovação.

---

### Task 4: Ajustar o template com o feedback dos pilotos

**Files:**
- Modify: `.../scratchpad/doc-template.md`

- [ ] **Step 1:** Incorporar ao template/brief qualquer correção de tom, profundidade ou estrutura pedida pelo Lucas nos pilotos. Se nenhum ajuste: registrar "template validado sem mudanças".

---

### Task 5: Fan-out — 20 repos restantes via subagents paralelos

**Files:** os 4 docs na raiz de cada repo listado abaixo.

**Interfaces:**
- Consumes: `doc-template.md` (validado), mapa de idioma README (abaixo).

**Idioma README por repo:** EN → `local-claude`, `ancalagon-llm`. PT → todos os demais.

**Procedimento por repo (aplicado a cada um da lista):**

- [ ] **Step A: Dispatch de subagent** (`general-purpose`), em ondas de ~5 para revisão gerenciável. Prompt = brief da Task 1 com `<REPO_PATH>` e `<IDIOMA_README>` preenchidos. O subagent lê, redige e **escreve** os 4 arquivos na raiz do repo, e retorna a lista de símbolos citados + nota de cobertura.

- [ ] **Step B: Spot-check** — para cada repo, confirmar 2-3 símbolos citados:
Run: `/opt/homebrew/bin/git -C <REPO_PATH> grep -n "<símbolo>"` → deve bater com o `caminho:linha` citado. Se falhar, devolver ao subagent para corrigir.

- [ ] **Step C: Commit + push por repo:**
```bash
/opt/homebrew/bin/git -C <REPO_PATH> add README.md MANUTENCAO.md AGENTS.md CLAUDE.md
/opt/homebrew/bin/git -C <REPO_PATH> commit -F - <<'MSG'
docs: adiciona README/MANUTENCAO/AGENTS/CLAUDE de manutenção

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LD8YtGu6p5osog8iFL1zTC
MSG
GIT_SSH_COMMAND='ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new' /opt/homebrew/bin/git -C <REPO_PATH> push   # pular nos 5 sem remote
```

**Lista dos 20 repos (checkbox por repo):**

Onda 1 (apps_mac):
- [ ] `/Users/lucas/git/apps_mac/ancalagon-llm` (README EN)
- [ ] `/Users/lucas/git/apps_mac/tm-backup`
- [ ] `/Users/lucas/git/apps_mac/keyboard-lock`
- [ ] `/Users/lucas/git/apps_mac/launchd-manager-tui`
- [ ] `/Users/lucas/git/apps_mac/network-guard`

Onda 2 (apps_mac cont. + apps_smaug):
- [ ] `/Users/lucas/git/apps_mac/kvm-setup`
- [ ] `/Users/lucas/git/apps_mac/solar-theme`
- [ ] `/Users/lucas/git/apps_mac/model-storage-switch` (sem remote → só commit)
- [ ] `/Users/lucas/git/apps_mac/tailscale-exit-node` (sem remote → só commit)
- [ ] `/Users/lucas/git/apps_smaug/setup-tachyon`

Onda 3 (local-claude + projetos):
- [ ] `/Users/lucas/git/local-claude` (README EN)
- [ ] `/Users/lucas/git/projetos/siaman_cristalina`
- [ ] `/Users/lucas/git/projetos/matchmaker-app`
- [ ] `/Users/lucas/git/projetos/aula_de_hoje_landing_page`
- [ ] `/Users/lucas/git/projetos/corne-xenon`

Onda 4 (projetos + intellissis):
- [ ] `/Users/lucas/git/projetos/FerramentaCompras`
- [ ] `/Users/lucas/git/intellissis/intellissis-web`
- [ ] `/Users/lucas/git/intellissis/intellissis-db-inventory` (sem remote → só commit)
- [ ] `/Users/lucas/git/intellissis/intellissis-infra` (sem remote → só commit)
- [ ] `/Users/lucas/git/intellissis/controle-acesso` (sem remote → só commit)

Nota: `local-claude` está na branch `docs/multi-repo-maintenance-spec` (spec commitada aí); commitar os docs na mesma branch ou fazer merge da branch antes — decidir no momento.

---

### Task 6: Varredura final de verificação

- [ ] **Step 1: Confirmar os 4 docs em todos os 22 repos**
Run (loop sobre os 22 caminhos):
```bash
for p in <22 caminhos>; do
  for f in README.md MANUTENCAO.md AGENTS.md CLAUDE.md; do
    [ -f "$p/$f" ] || echo "FALTA: $p/$f"
  done
done
```
Expected: nenhuma linha "FALTA".

- [ ] **Step 2: Confirmar commit/push**
Run: `for p in <17 com remote>; do /opt/homebrew/bin/git -C "$p" status -sb | head -1; done`
Expected: cada um "nothing to commit"; branches à frente = 0 após push (ou reportar pendências).

- [ ] **Step 3: Relatório final** ao Lucas: repos feitos, símbolos spot-checked, o que ficou de fora nos repos grandes, e os 5 sem-remote (só commit local).

## Self-Review

- **Spec coverage:** os 4 docs (README/MANUTENCAO/AGENTS/CLAUDE) → Task 1 (template) + Task 2/3 (piloto) + Task 5 (fan-out). Idioma → Global Constraints + mapa na Task 5. Merge → Global Constraints + Task 2 Step 2. Precisão → spot-check em Task 2/3/5. Commit/push → Task 5 Step C. Escopo 22 repos → Task 5 lista (20) + 2 pilotos = 22. ✓
- **Placeholder scan:** esqueletos e brief são concretos; comandos com paths reais. ✓
- **Type consistency:** nomes de arquivo (README.md/MANUTENCAO.md/AGENTS.md/CLAUDE.md) e paths consistentes em todas as tasks. ✓
