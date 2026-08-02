---
name: omp-fleet
description: Standalone runner + fleet orchestrator for Oh My Pi (`omp`), a coding-agent CLI that reaches your existing OpenAI Codex subscription through a different harness. Does THREE things and always EXECUTES them (never just describes): (1) general code tasks via `omp -p`, (2) cheap high-volume context gathering on the 25x-cheaper model tier, and (3) parallel fan-out — both in-process subagents and multi-process lanes. Defaults locked: provider pinned to your own subscription, never a metered fallback. Triggers on: "use omp", "run omp", "omp exec", "oh my pi", "ask omp to ...", "spawn an omp fleet", "parallel omp", "cheap recon pass", and any request to delegate code-level work to omp.
---

# OMP Fleet — Standalone Action Runner

> A single self-contained skill for driving [Oh My Pi](https://www.npmjs.com/package/@oh-my-pi/pi-coding-agent) (`omp`) from any agent (Claude Code, Cursor, or your own harness). No external control plane required. Drop this file into `.claude/skills/omp-fleet/SKILL.md` (or your agent's skills dir) and go.
>
> Companion to [`codex-fleet`](../codex-fleet) — same doctrine, different runtime. Read that one for fleet fundamentals (briefs, worktree isolation, lane discipline); this one covers what changes when the lane is `omp` instead of `codex exec`.
>
> Built and battle-tested by [Avenox](https://avenox.lol). Share freely.

## CRITICAL: This is an ACTION skill, not commentary

When invoked you MUST:

1. **Actually invoke `omp -p` via the Bash tool.** Never write instructions for the user to run themselves.
2. **Default to background execution** (`run_in_background: true`) for anything likely to take >10s.
3. **For multiple independent jobs, fire them ALL in parallel** in a single message — but read the RAM section first, because omp lanes are expensive in memory and the ceiling is much lower than with Codex.
4. **Summarize from logs** after each job; don't dump raw stdout unless asked.

## The one thing everybody gets wrong

**There is no `omp exec` subcommand.** If you're coming from `codex exec`, the equivalent is `-p` / `--print`:

```bash
omp -p "your prompt"          # correct — non-interactive, process and exit
omp exec "your prompt"        # WRONG — no such subcommand
```

## Prerequisites

- `omp` installed and authenticated against at least one provider (`omp --help`, `omp usage`).
- An OpenAI Codex subscription is the assumed default here. `omp usage` shows every authenticated account and its remaining limit — run it before a fleet; that's your real capacity ceiling.

## Defaults (locked in)

| Setting | Value | When to override |
|---|---|---|
| Provider | **your own subscription, pinned** | never — see the provider lock below |
| Executor model | `openai-codex/gpt-5.6-sol:xhigh` | a cheaper tier for mechanical lanes |
| Recon model | `openai-codex/gpt-5.6-luna:xhigh` | when the lane must *decide*, not just read |
| Config overlay | `--config <skill dir>/codex-only.yml` | always pass it on unattended lanes |
| Approvals | `--approval-mode yolo` | drop it if a human is watching and wants prompts |
| Tools | **all of them, always** | never pass `--no-tools` / `--no-lsp` / `--no-skills` |
| Timebox | `--max-time 45m` | tune per lane; always set something |

Model selector syntax is **`provider/model:thinking`** — e.g. `openai-codex/gpt-5.6-sol:xhigh`. Thinking levels: `low`, `medium`, `high`, `xhigh`, `max`.

---

## Part 1 — The provider lock (do this first)

`omp` aggregates a *lot* of providers. Two of its defaults combine into a real hazard:

- `retry.modelFallback` defaults to **`true`**, so a rate-limited or erroring lane can re-route mid-run.
- Model ids **fuzzy-match**. Ask for `gpt-5.6-sol` and you may get OpenRouter's `openai/gpt-5.6-sol` — a *different, metered* route — instead of the one on your subscription.

If you have any metered provider key configured (OpenRouter, OpenCode, a gateway), an unattended fleet can quietly spend real money outside your plan. Two independent guards — use both:

**1. Always use fully-qualified model ids.** The `provider/` prefix is what defeats fuzzy matching:

```bash
omp -p --model openai-codex/gpt-5.6-sol:xhigh "..."   # pinned
omp -p --model gpt-5.6-sol "..."                      # ambiguous — don't
```

**2. Ship a per-run config overlay.** `codex-only.yml` next to this skill disables the metered providers and turns fallback off **for that run only**, without touching the user's real `~/.omp/agent/config.yml`:

```bash
omp -p --config ~/.claude/skills/omp-fleet/codex-only.yml "..."
```

**Verify it.** `--mode json` and confirm the provider on the `message_end` event:

```bash
omp -p --mode json --config <overlay> "ping" 2>&1 | grep -o '"provider":"[^"]*"' | sort -u
# want: "provider":"openai-codex"
```

Do this once per new machine and once after any omp upgrade. It costs one call and it's the difference between "my sub" and "my credit card."

---

## Part 2 — Model economics (the actual reason to use omp)

Measured on one machine, same prompt, same harness, both on the Codex subscription route:

| model | input $/M | output $/M | 30K-token turn |
|---|---|---|---|
| `gpt-5.6-sol` | **$5.00** | **$30.00** | ~$0.15 |
| `gpt-5.6-luna` | **$0.20** | **$1.20** | ~$0.006 |

**Exactly 25×** on both input and output.

The number that matters more than the ratio: **omp sends ~30K input tokens of system prompt and tool schemas before your prompt even starts.** On the expensive tier that's ~$0.15 *per turn* just to say hello. Short prompts are not cheap prompts — model choice dominates completely.

### Tiering rule: cheap reads, expensive decides

- **`luna`** — context gathering, file and symbol discovery, inventory sweeps, "where does X live", first-pass summarization, mechanical edits against a verified spec, and any high-fan-out recon where *you* will do the synthesis.
- **`sol`** — architecture, review, security, ambiguity resolution, anything that writes to a shared branch, anything whose wrong answer costs more than the 25× saving.

Do not run a 20-lane recon sweep on the expensive tier. That is the mistake this table exists to prevent.

---

## Part 3 — Spawn recipe (one lane)

```bash
omp -p \
  --config ~/.claude/skills/omp-fleet/codex-only.yml \
  --model openai-codex/gpt-5.6-sol:xhigh \
  --approval-mode yolo \
  --cwd <LANE_DIR> \
  --max-time 45m \
  --mode json \
  --session-dir <LANE_DIR>/.omp-session \
  "<SELF-CONTAINED LANE BRIEF>" \
  > /tmp/lane-A.out.log 2> /tmp/lane-A.err.log
```

Fire with `run_in_background: true`. The brief is the lane's **entire contract** — goal, files it OWNS, files it must NOT touch (and which sibling owns them), the acceptance check, and how to report done/failed. A delegate cannot see your conversation.

Flag notes:

- `--cwd` anchors the lane. `--add-dir <path>` (repeatable) grants read access beyond it.
- `--max-time 45m` is a hard stop. `codex exec` has no equivalent — use it on every unattended lane.
- `--mode json` emits one JSON object per line (`session`, `agent_start`, `message_start/update/end`, `turn_end`, `agent_end`). `message_end.usage` carries `input`/`output`/`cacheRead`/`reasoningTokens`/`cost`; `message_end.provider` is your lock verification.
- `--session-dir` per lane stops sessions colliding. `--no-session` for throwaway probes.
- `--profile <name>` gives a lane fully isolated auth, sessions, settings, and caches.
- Drop `--model` entirely and the overlay's `modelRoles.default` resolves it.

### Resume and continue

```bash
omp --continue "follow-up"           # continue the previous session
omp --resume <id-prefix> "follow-up" # resume a specific one
omp --export <session.jsonl>         # render a session to HTML
```

---

## Part 4 — Three parallelism modes

### Mode 1 — In-process subagent fan-out (the distinctive one)

A single `omp` process can drive its own subagents concurrently (`task.maxConcurrency`, default 32, recursion depth 2). Bundled roster: `scout`, `librarian`, `reviewer`, `security-reviewer`, `designer`, `sonic`, `task`. Materialize and edit them with:

```bash
omp agents unpack --project     # writes ./.omp/agents
omp agents unpack               # writes ~/.omp/agent/agents
```

`task.agentModelOverrides` routes each agent to its own model — the shipped overlay puts `scout`/`librarian`/`sonic` on the cheap tier and `reviewer`/`security-reviewer`/`designer` on the expensive one. So one lane can fan out a dozen cheap readers and pay ~$0.006 each while reserving judgement for the model that's worth it.

Write the brief to *ask for* the fan-out — omp decides internally whether to spawn subagents.

Best for: "map this subsystem", "find every caller of X", "inventory the drift across these 40 files".

### Mode 2 — `omp cleanse` (paved parallel fixer)

```bash
omp cleanse -n 8 -m openai-codex/gpt-5.6-sol:xhigh -t
```

Detects project diagnostics and fixes them with **file-disjoint** weighted subagents; `-t` also runs configured test suites. Disjointness is already solved for you — try this before hand-rolling a lint/diagnostic fleet. Dry-run on a scratch branch the first time.

### Mode 3 — Multi-process lanes (a true fleet)

N independent `omp -p` processes, one per claimed region. All the discipline from [`codex-fleet`](../codex-fleet) Part 3 applies unchanged: disjoint OWNS lists, stagger spawns 2–5s, `caffeinate -i` on macOS, worktree-per-lane for concurrent writes, and **completions are claims, not evidence** — run the acceptance check yourself.

For write isolation you can also try omp's built-in `task.isolation` (`mode: apfs|reflink|block-clone`, `merge: patch|branch`) instead of git worktrees. Cheaper on a copy-on-write filesystem, but prove it on a throwaway branch before trusting lane output to it.

---

## Part 5 — GOTCHAS

### An omp lane costs ~1.7GB — and ~75% of that is MCP servers, not omp

Measured peak RSS across the full process tree, one lane, trivial prompt: **~1700 MB.** For comparison a `codex exec` lane measured ~108 MB. But that headline number is misleading in *both* directions, and the breakdown is what you actually need:

| process | RSS |
|---|---|
| `bun` — **the omp harness itself** | **~330–460 MB** |
| Claude Code MCP server (project) | ~150 MB |
| `firecrawl-mcp` + its `npm exec` parent | ~134 + ~96 MB |
| `mcp-server-supabase` + parent | ~107 + ~93 MB |
| `context7-mcp` **×2** + parents | ~100 + ~98 + ~95 + ~93 MB |
| plugin MCP server | ~79 MB |

**omp boots every MCP server it can discover, on every launch.** It imports the Claude Code ecosystem wholesale — global, project, *and* plugin MCP configs. Three compounding wastes:

1. **The `npx` double-cost.** Every `npx`-launched MCP server keeps a resident `npm exec` parent process alongside the real server — roughly **+50% memory per server for nothing**.
2. **Duplicate servers.** Two `context7-mcp` instances ran simultaneously from different npx cache entries (one pinned `@latest`, one not) — ~380MB for one server's worth of capability.
3. **Per-lane duplication.** Every lane spawns its *own* full copy of the set. Four lanes is four MCP fleets. This, not the harness, is what makes omp fleets expensive.

**So the honest harness-to-harness comparison is ~460MB (omp) vs ~108MB (codex) — about 4×, not 15×.** The `codex-fleet` spawn template passes `-c mcp_servers={}`, which is exactly why Codex lanes measure so small; it's a fair-fight difference in *default configuration*, not runtime weight.

**Fleet sizing:**

- Budget from what you actually measure on your box, not from this table — your MCP set is yours.
- With MCP left on, the `codex-fleet` ~20-lane rule does **not** transfer: ~20 omp lanes is ~34GB. Realistically **4–8 concurrent** on a 16–32GB machine.
- **Prefer Mode 1 (in-process subagents) over Mode 3 (multi-process lanes).** One omp process running 12 subagents pays the MCP tax *once*; 12 separate lanes pay it twelve times. This is the single biggest memory lever available.
- **`--profile <name>` is the clean lane isolation.** A fresh profile doesn't inherit the discovered MCP set, so lanes start lean. It isolates auth too, so log in once per profile before using it in a fleet (`omp --profile fleetlane` interactively, then reuse it).
- Things that do **not** work, so don't waste time: `mcpServers: {}` in a `--config` overlay is a no-op (overlays deep-merge, so an empty map merges nothing), `mcp.enableProjectConfig: false` doesn't stop globally-discovered servers, and `--no-extensions` / `--no-lsp` change nothing (LSP is not the cost).

Measure your own tree — sum the **descendant closure**, not just the root pid, or you'll under-report by more than half:

```bash
omp -p --no-session "<some real task>" & ROOT=$!
while kill -0 $ROOT 2>/dev/null; do
  ps -Ao rss=,pid=,ppid= | awk -v root=$ROOT '
    {rss[$2]=$1; pp[$2]=$3; pid[NR]=$2; n=NR}
    END{d[root]=1; ch=1
      while(ch){ch=0; for(i=1;i<=n;i++){p=pid[i]; if(!d[p]&&d[pp[p]]){d[p]=1;ch=1}}}
      s=0; for(i=1;i<=n;i++) if(d[pid[i]]) s+=rss[pid[i]]
      print s/1024" MB"}'
  sleep 2
done
```

Swap `rss=,pid=,ppid=` for `rss=,pid=,ppid=,args=` and print the argv to see exactly which servers your lanes are paying for. Worth doing once — you may find, as above, that you're running a server twice.

> **While you're in there:** check what your MCP servers put in their argv. One of the servers observed here passes a live API access token as a command-line argument, which makes it readable by any process on the box via `ps`. That's a property of that server, not of omp, but omp launching it per-lane multiplies the exposure.

### Everything else

| Symptom / trap | Fix |
|---|---|
| `omp exec ...` → unknown command | There is no `exec`. Use `-p` / `--print`. |
| Lane silently answered by a metered provider | Fully-qualified `provider/model:thinking` **and** the `codex-only.yml` overlay. Verify with `--mode json`. |
| `timeout 60 omp ...` → `command not found` | macOS has no `timeout(1)`. Use omp's own `--max-time`, or install coreutils for `gtimeout`. |
| A raw API key appeared in your logs | `omp token <provider>` **prints the secret to stdout**. Never run it inside a lane, a CI job, or a transcript you'll share. Use `omp usage` to check auth instead. |
| Liveness heuristics copied from Codex read backwards | **omp streams to STDOUT**; `codex` ≥0.142 streams session output to STDERR. A 0-byte `.out.log` means something different in each runtime. |
| Prompt is tiny but the bill isn't | ~30K tokens of system prompt + tool schemas per turn. Model choice dominates; prompt length barely matters. |
| `--print-thoughts` shows nothing | The Codex responses API returns *encrypted* reasoning with an empty summary. Absence of visible thinking is expected, not a bug. |
| Can't confirm the thinking level actually applied | Reasoning-token counts move only slightly between `low` and `xhigh` on easy prompts. Judge effort by outcome, not by the flag. |
| A lane behaves differently than expected in someone else's repo | omp auto-discovers Claude user+project skills, agents skills, and Claude commands. Pin with `--skills <globs>` when a lane must be hermetic. |
| Fleet config bled into interactive use | Never edit `~/.omp/agent/config.yml` for fleet purposes. Everything fleet-specific goes in the per-run `--config` overlay. |

---

## Part 6 — Other features worth knowing

- **`--prewalk` / `--plan-yolo`** — built-in expensive-plan / cheap-execute split. `--plan-yolo` starts read-only, auto-approves the plan on first resolve, then implements with `--plan-yolo-into`; `--prewalk` switches to a cheap model at the first edit once the plan's checklist exists. Pair with `--prewalk-into <cheap model>` to plan on the strong tier and grind on the cheap one in one process. Both default OFF.
- **`--from-claude` / `--from-codex`** — imports an existing Claude Code or Codex session into omp. A real handoff seam: give a lane your accumulated context instead of re-deriving it in the brief.
- **`--advisor`** — a passive reviewer that reads each turn and injects notes. Worth switching on for long unattended write lanes as a cheap in-band quality stop.
- **`omp bench <models...> --json`** — time-to-first-token and throughput per model. Settle "is the cheap tier fast enough for this lane" with data.
- **`omp usage`** — per-account limit bars across every authenticated provider. Run before a fleet.
- **`omp worktree list|clear --json`** — omp manages its own worktrees. Sweep at closeout; a stale worktree is unfinished work.
- **`omp models`** — the full catalog, grouped by provider. Use it to find the exact qualified id for the lock.
- **`--mode rpc` / `rpc-ui`** — programmatic drive, if you want to own a lane from your own supervisor process.

---

## Choosing between omp and Codex

| Your constraint | Reach for |
|---|---|
| Memory / many concurrent lanes | **`codex exec`** — ~108MB vs ~460MB bare, ~1700MB once omp's discovered MCP servers boot |
| Cost on high-volume reading | **omp** — the 25× cheap tier |
| One task, many internal readers | **omp** — in-process subagent fan-out |
| Hard per-lane timebox | **omp** — `--max-time` |
| Structured lane telemetry | **omp** — `--mode json` with per-turn usage and cost |
| Image generation | **`codex exec`** — see [`codex-fleet`](../codex-fleet) Part 2 |
| A genuine second opinion | Run both. Different harness, different scaffolding, same underlying sub. |

---

## Credits

Built and maintained by **Avenox** — [avenox.lol](https://avenox.lol). Companion to [`codex-fleet`](../codex-fleet). Feedback and improvements welcome, especially measurements from other machines — the RAM and cost numbers above are from a single box and deserve corroboration.
