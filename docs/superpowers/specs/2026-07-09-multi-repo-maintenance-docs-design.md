# Design — Documentação de manutenção multi-repo

**Data:** 2026-07-09
**Autor:** Lucas + Claude Code
**Status:** Aprovado (design), pendente plano de implementação

## Objetivo

Criar/atualizar um conjunto padronizado de 4 documentos em cada repositório
criado pelo Lucas (ou herdado, onde ele é dono), para instruir humanos e LLMs
locais sobre como fazer mudanças, manutenção e onde ficam as funções importantes.
Meta: facilitar as próximas janelas do Claude Code, o LLM local (Ancalagon) e
manutenção humana, em qualquer operação (criação, edição, etc).

## Escopo — 22 repositórios

**Teus, já espelhados no homelab (16):**
`local-claude`, `apps_mac/ancalagon-llm`, `apps_mac/tm-backup`,
`apps_mac/keyboard-lock`, `apps_mac/launchd-manager-tui`, `apps_mac/network-guard`,
`apps_mac/kvm-setup`, `apps_mac/solar-theme`, `apps_smaug/setup-tachyon`,
`apps_smaug/duckdns-update`, `projetos/siaman_cristalina`, `projetos/matchmaker-app`,
`projetos/aula_de_hoje_landing_page`, `projetos/corne-xenon`,
`intellissis/intellissis-web`, `intellissis/ocr-pipeline-local`

**Sem remote (mas teus) (5):**
`apps_mac/model-storage-switch`, `apps_mac/tailscale-exit-node`,
`intellissis/intellissis-db-inventory`, `intellissis/intellissis-infra`,
`intellissis/controle-acesso`

**Herdado do afcavalcanti (1):**
`projetos/FerramentaCompras`

**Fora de escopo (decisão explícita):**
`Arduino_Projetos` (snapshot de libs de terceiros), `peon-ping` (fork da org PeonPing),
`lucaspwo.github.io` (site Pages), e os 4 do bitbucket `fourakis`
(`idm-03`, `new-map-comb`, `intellissis.geracao.alimentadores`, `intellissis-pgcollect`).

## Os 4 documentos (todos na raiz de cada repo)

Papéis distintos, sem redundância. Conteúdo profundo mora em um lugar só; os
arquivos de agente apontam para ele.

### README.md — porta de entrada humana
- **Idioma:** inglês nos repos GitHub **públicos**; PT nos privados/empresa/sem-remote
  (visibilidade detectada via `gh repo view <repo> --json visibility`).
- **Seções:** o quê/porquê (1 parágrafo) · stack/requisitos · instalação/setup ·
  como rodar (comandos principais) · estrutura de pastas (alto nível) ·
  links para MANUTENCAO.md / AGENTS.md / CLAUDE.md · licença (se aplicável).

### MANUTENCAO.md — guia profundo humano
- **Idioma:** PT (todos).
- **Seções:** visão de arquitetura (como as peças se encaixam) · mapa de módulos/pastas
  com propósito · **onde ficam as funções/pontos-chave** (`arquivo:linha`) ·
  fluxos de dados principais · **receitas de mudança comuns** ("adicionar X",
  "corrigir Y", "criar feature Z") · build/test/lint/deploy · gotchas e decisões de design ·
  dependências externas e integrações.

### AGENTS.md — mapa denso para LLM local (Ancalagon)
- **Idioma:** inglês (todos). LLMs locais menores seguem instrução técnica em EN de
  forma mais confiável; conteúdo estruturado é quase language-neutral.
- **Seções:** project one-liner + stack · file/dir map (path → purpose), conciso ·
  **key symbols index** (função/classe → `arquivo:linha` → o que faz) ·
  commands (build/test/lint/run, exatos) · conventions & constraints (do/don't) ·
  common change recipes (imperativo, passo a passo) · safety rails (o que NÃO tocar).

### CLAUDE.md — fino, específico do Claude Code
- **Idioma:** PT (todos).
- **Seções:** 1-linha do projeto · comandos essenciais (build/test/run) ·
  top 3-5 gotchas · ponteiros ("arquitetura → MANUTENCAO.md, mapa de símbolos → AGENTS.md") ·
  regra de commit/push (lembrar do espelhamento multi-remote; nos sem-remote, só commit local) ·
  referência ao CLAUDE.md global quando relevante.

## Regras transversais

- **Merge, não sobrescrever.** Nos repos que já têm README/CLAUDE/AGENTS, preservar
  conteúdo bom existente, reorganizar para o template e complementar o que falta.
- **Precisão verificável.** Todo símbolo/caminho citado deve ser real. Referências
  `arquivo:linha` inventadas = rejeitadas. Claude faz spot-check antes do commit de cada repo.
- **Commit + push por repo.** Ao final de cada repo, commit dos 4 docs e push
  (o `git push` já vai para todos os remotes via pushurls configuradas). Nos 5 sem
  remote: apenas commit local. Nunca usar `--no-verify`.

## Execução

1. **Template canônico** — escrever os 4 esqueletos + regras de qualidade
   (este documento serve de base; o plano detalha o texto-modelo).
2. **Piloto** — `ocr-pipeline-local` (Python, ativo, já tem CLAUDE+AGENTS → exercita o
   merge) e `duckdns-update` (minúsculo → exercita o outro extremo). Lucas aprova o resultado.
3. **Fan-out** — 1 subagent por repo restante (agentes `Explore`/`general-purpose`),
   lê a fundo e redige seguindo o template; Claude revisa cada saída.
4. **Commit/push por repo.**

## Estratégia de sub-agentes (fan-out)

- Cada subagent recebe: caminho do repo, o template canônico, as regras de idioma
  (incl. visibilidade do repo), e a política de merge.
- Cada subagent retorna os 4 documentos (ou diffs de merge) + a lista de
  `arquivo:linha` citados, para o spot-check.
- Repos grandes/legados exigem mapeamento seletivo (pontos-chave, não exaustivo);
  o subagent deve declarar explicitamente o que cobriu e o que ficou de fora
  (sem cap silencioso).

## Riscos e mitigação

- **Drift futuro:** conteúdo profundo concentrado em MANUTENCAO/AGENTS; CLAUDE fino
  aponta para eles → um só lugar para atualizar por eixo.
- **Alucinação de símbolos:** exigência de citar `arquivo:linha` real + spot-check.
- **Repos heterogêneos:** template com seções fixas, mas profundidade escalada ao repo.

## Pendências resolvidas (defaults aprovados)

- Spec deste projeto vive em `local-claude/docs/superpowers/specs/`.
- Os 4 docs vão na **raiz** de cada repo.
