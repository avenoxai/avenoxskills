# avenoxskills

Agent skills built and battle-tested in production by [Avenox](https://avenox.lol).

These aren't demos. Each one runs real work — shipping YouTube videos, driving
Codex fleets, packaging codebases for external review — and each carries the
gotchas that only show up after something breaks at 2am. That's the part worth
having.

Compatible with [Claude Code](https://claude.com/claude-code), Cursor, and any
harness that reads `SKILL.md`-style agent skills.

## Install

Copy any skill directory into your agent's skills folder:

```bash
git clone https://github.com/avenoxai/avenoxskills.git
cp -R avenoxskills/skills/codex-fleet ~/.claude/skills/
```

Or take just the one file you want — every skill is self-contained except the
video trio, which shares `avenox-studio/` (see below).

## The skills

### Agent operations

| Skill | What it does |
|---|---|
| **[codex-fleet](skills/codex-fleet)** | Standalone Codex CLI runner + fleet orchestrator. General `codex exec` tasks, `gpt-image-2` image generation, and parallel multi-lane fleets with worktree isolation. Dependency-free — no control plane required. |
| **[omp-fleet](skills/omp-fleet)** | The same job for [Oh My Pi](https://www.npmjs.com/package/@oh-my-pi/pi-coding-agent) (`omp`) — a second coding-agent CLI onto the same Codex subscription. Provider pinning so a lane can't fall through to a metered aggregator, a 25×-cheaper model tier for recon, and in-process subagent fan-out. Includes the measured RAM comparison that decides which harness you actually want. |
| **[fable-orchestration](skills/fable-orchestration)** | Delegation policy for a multi-model stack: when the main loop runs on a scarce top-tier model, what goes to cheaper sub-agents, and what goes to Codex lanes. Routes on *difficulty*, not just task type. |

### External model review

| Skill | What it does |
|---|---|
| **[gptpro](skills/gptpro)** | Export a monorepo into review-ready zip bundles for a non-agentic frontier model — `node_modules`-free, split by subsystem, with a secret scan that hard-aborts the export rather than shipping a key to a chat UI. |
| **[gptpro-handoff](skills/gptpro-handoff)** | The workflow around it: author the prompt, receive the report, verify every finding against the *live* codebase before implementing. Includes the prompt house style. |

### Video production

A local-first, agent-operated YouTube pipeline. Nothing uploads to render.

| Skill | What it does |
|---|---|
| **[avenox-video](skills/avenox-video)** | The router — read this first. 7-step pipeline from intake to export. |
| **[avenox-roughcut](skills/avenox-roughcut)** | Transcript-driven rough cut: silence removal *and* flub/retake removal, in the right order. |
| **[avenox-graphics](skills/avenox-graphics)** | Brand-locked motion graphics via HyperFrames, composited onto the cut. |
| **[avenox-thumbnail](skills/avenox-thumbnail)** | High-CTR thumbnail factory for a mascot-driven channel. Parallel `gpt-image-2` jobs, hook-pattern playbook, hard safety rules. |

The three video skills share runtime files in **[`avenox-studio/`](avenox-studio)**
— scripts, the `edit.json` template, and the brand spec:

```bash
export STUDIO_ROOT="$PWD/avenox-studio"
export STUDIO_JOBS="$HOME/video/projects"   # heavy media — keep OUT of cloud sync
cp avenox-studio/brand/frame.template.md avenox-studio/brand/frame.md
cp avenox-studio/brand/caption-corrections.example.json avenox-studio/brand/caption-corrections.json
```

### Blockchain

| Skill | What it does |
|---|---|
| **[chainscan](skills/chainscan)** | Multi-chain block explorer via the Etherscan V2 unified API + Foundry `cast` fallbacks. Contract ABI/source, txs, logs, balances, token info across 60+ chains. One key, one endpoint. |

## Bring your own assets

Two skills expect files this repo deliberately doesn't ship:

- **`avenox-thumbnail`** needs your own mascot reference in `assets/`. The
  mascot is channel identity — yours should be yours. It also needs tool logos,
  which are third-party trademarks; the fetch recipe is included instead of the
  files. See [`skills/avenox-thumbnail/assets/README.md`](skills/avenox-thumbnail/assets/README.md).
- **`avenox-graphics`** reads `avenox-studio/brand/frame.md`, which you create
  from the template. Lock it early — visual consistency compounds, and changing
  it mid-channel costs more than getting it slightly wrong at the start.

## Requirements

Varies by skill; each `SKILL.md` states its own.

- `codex-fleet` — Codex CLI 0.128+, authenticated
- `omp-fleet` — `omp` (`@oh-my-pi/pi-coding-agent`), authenticated against a
  provider; budget ~0.5GB RAM per concurrent lane bare, ~1.7GB with a typical
  MCP set auto-discovered
- `gptpro` — `zip`, `rsync`
- video skills — macOS (hardware encode, `mlx-whisper` on Apple Silicon),
  `ffmpeg`, `python3`, MLT/`melt`, Node. Most work on Linux with `libx264` and a
  CUDA whisper build substituted in.
- `chainscan` — an Etherscan V2 API key; Foundry for `cast` fallbacks

## A note on the gotchas

The sections labelled **GOTCHAS** are the highest-value part of this repo. A few
that cost real hours:

- `auto-editor` v29 leaks the last `--cut-out` range as a positional input file.
  Use ffmpeg's `select` filter for content cuts.
- Codex's greedy `-i` parse eats your prompt unless you put `--` before it.
- An `omp` lane measures ~1700MB against a Codex lane's ~108MB — but ~75% of
  that is MCP servers omp auto-discovers and boots *per lane*, not the harness
  (~460MB). Every `npx`-launched MCP server also keeps a resident `npm exec`
  parent, so you pay ~50% extra per server for nothing.
- `omp` has no `exec` subcommand — non-interactive is `-p`. And its model ids
  fuzzy-match, so an unpinned lane can answer from a metered aggregator
  instead of your subscription.
- Parallel `gpt-image-2` jobs share an image cache and can return duplicate
  renders — md5 the batch, re-fire dupes solo.
- SVG `feTurbulence` grain must use a fixed seed or rendered frames flicker.
- `auto-editor` and `npx` both need the certifi SSL fix or their downloads fail.

## License

MIT — see [LICENSE](LICENSE). Use them, fork them, improve them.

Issues and PRs welcome, especially "this broke on my setup" reports.
