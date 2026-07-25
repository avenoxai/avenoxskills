---
name: codex-fleet
description: Standalone Codex CLI runner + fleet orchestrator. Does THREE things and always EXECUTES them (never just describes): (1) general code tasks via `codex exec`, (2) high-quality image generation via Codex's built-in `gpt-image-2` tool, and (3) parallel multi-lane fleets — spawning many `codex exec` delegates at once with worktree isolation. Defaults locked: model `gpt-5.6-sol`, reasoning `high`, `--skip-git-repo-check` always. For multiple independent jobs, fire them ALL in parallel — compute is not the constraint, throughput is. Triggers on: "use codex", "run codex", "codex exec", "imagegen", "generate image", "make image", "render this", "ask codex to ...", "have codex ...", "spawn a fleet", "parallel codex", any image-asset request (icons/sigils/banners/portraits/backgrounds/sprites/UI assets/mockups/photoreal/etc.), and any request to delegate code-level work to Codex.
---

# Codex Fleet — Standalone Action Runner

> A single self-contained skill for driving the [Codex CLI](https://github.com/openai/codex) from any agent (Claude Code, Cursor, or your own harness). No external control plane required — everything here runs against a plain local `codex` install. Drop this file into `.claude/skills/codex-fleet/SKILL.md` (or your agent's skills dir) and go.
>
> Built and battle-tested by [Avenox](https://avenox.lol). Share freely.

This skill does three things and ALWAYS executes them, never describes them:

1. **General Codex CLI tasks** — code review, refactor, multi-file edits, analysis, diagnosis, anything you'd hand to a peer-AI for parallel processing.
2. **Image generation** — real rendered images via Codex's built-in `gpt-image-2` tool: backgrounds, portraits, icons, sigils, banners, UI assets, sprites, mockups, photoreal, infographics.
3. **Fleets** — spawning many `codex exec` delegates in parallel (one lane or twenty), with worktree isolation for concurrent write lanes.

## CRITICAL: This is an ACTION skill, not commentary

When invoked you MUST:

1. **Actually invoke `codex exec` via the Bash tool.** Never write instructions for the user to run themselves.
2. **Default to background execution** (`run_in_background: true`) for any task likely to take >10s. This lets the main agent continue other work in parallel while Codex runs. The harness notifies on completion.
3. **For multiple independent jobs, fire them ALL in parallel.** Codex sessions don't contend. Compute is not the bottleneck — throughput is. If the user asks for 4 images or 3 codex investigations, that's 4 or 3 simultaneous Bash calls in one message, all `run_in_background: true`.
4. **Summarize results from logs** after each background job completes — don't dump raw stdout unless asked.

If the user's request is "use codex to X" or "run codex on X", run `codex exec ... "X"`. Don't wrap, don't paraphrase, don't ask "should I proceed" — just go.

## Prerequisites

- Codex CLI 0.128+ installed and authenticated (`codex --version`). Reasoning tiers `low`/`medium`/`high`/`xhigh` require 0.128+.
- For the image-gen **CLI fallback** and `gpt-image-1.5` transparency path only: `OPENAI_API_KEY`. The built-in `image_gen` tool uses your Codex subscription and needs no key.

## Defaults (locked in)

| Setting | Value | When to override |
|---|---|---|
| Model | `gpt-5.6-sol` | `-m <model>` only if user specifies |
| Reasoning effort | `high` | `xhigh` ONLY on explicit user request ("use xhigh", "max reasoning", "deep"); `medium`/`low` for cheap mechanical lanes |
| Service tier | **standard — fast is OFF** | see the note below; opt in per-call only |
| Sandbox | `read-only` | `workspace-write` for edits; `danger-full-access` for image gen or network (ask first) |
| `--skip-git-repo-check` | always | always |
| Stderr | suppressed (`2>/dev/null`) | only show when debugging |
| `--color never` | recommended | when you need to grep stdout cleanly |

Reasoning levels available (codex 0.128+): `low`, `medium`, `high`, `xhigh`. Lean toward `high`. Don't downgrade to "save effort" unless the lane is genuinely mechanical.

> **Fast tier is OFF by default — do not add it.** `-c service_tier=fast -c fast_default_opt_out=false` buys ~1.5× speed at ~2.5× rate cost. That trade is wrong for how this skill is used: everything here is background-first and parallel, so nobody is staring at a single lane's latency, and burning 2.5× rate on twenty lanes drains your limits for no wall-clock gain. Standard tier gives you the same quality plus rate-limit headroom. Every example in this file omits it deliberately. Opt in per-call only when a human is actively blocked on one foreground result — never for fleets, never as a global default.

---

## Part 1 — General Codex Tasks

### Base command

```bash
codex exec --skip-git-repo-check \
  -m gpt-5.6-sol \
  -c model_reasoning_effort=high \
  --sandbox read-only \
  "<PROMPT>" 2>/dev/null
```

### Sandbox quick reference

| Use case | Flags |
|---|---|
| Read-only review / analysis / diagnosis (default) | `--sandbox read-only` |
| Apply local edits | `--sandbox workspace-write --full-auto` |
| Network access or broad system access | `--sandbox danger-full-access --full-auto` (confirm with user first) |

For a working dir other than CWD: add `-C <DIR>`.
For escalated reasoning: replace `model_reasoning_effort=high` with `=xhigh`.

### Background-first invocation pattern

Run any non-trivial codex task in the background. Don't block the main thread:

```
Bash tool call:
  command: codex exec --skip-git-repo-check -m gpt-5.6-sol \
           -c model_reasoning_effort=high \
           --sandbox read-only \
           "Review src/foo.ts for race conditions and report findings." 2>/dev/null
  run_in_background: true
```

Then continue other work. When the background notification fires, read the log/output and summarize.

For tasks where you genuinely need the result before doing anything else (rare), run foreground.

### Parallelization (the default for multiple jobs)

If the user asks for N independent codex investigations, fire all N as separate `run_in_background: true` Bash calls **in a single message**. They run simultaneously. Compute is not constrained.

Example: "have codex review the contracts AND the backend AND the frontend" → 3 parallel codex jobs, not sequential.

### Resume

To continue a previous session (preserves model, reasoning, sandbox of the original):

```bash
echo "follow-up prompt" | codex exec --skip-git-repo-check resume --last 2>/dev/null
```

When resuming, **do not pass `-m`, `-c model_reasoning_effort`, or `--sandbox`** — they inherit. Only add flags if the user is explicitly changing the configuration.

### Critical evaluation of Codex output

Codex runs on OpenAI's models with their own training cutoffs. Treat it as a peer, not an authority:

- Trust your own knowledge when confident; push back on Codex claims you know to be wrong.
- Verify via web search or live docs when uncertain — especially for model names, recent library versions, post-cutoff API changes.
- For substantive disagreements, resume and discuss as a peer:
  ```bash
  echo "I disagree with [X] because [Y]. What's your take?" \
    | codex exec --skip-git-repo-check resume --last 2>/dev/null
  ```
- Frame as discussion, not correction. Either AI can be wrong. If genuine ambiguity remains, surface it to the user.

### Error handling

- If `codex --version` or `codex exec` exits non-zero, stop and report. Do not retry blindly.
- High-impact flags (`--full-auto`, `--sandbox danger-full-access`, `--dangerously-bypass-approvals-and-sandbox`) require explicit user OK before first use in a session — after that you can keep using them within the same task scope.

---

## Part 1.5 — Multi-Image Reference Chains (CRITICAL)

For both general codex tasks (passing images for analysis) AND image generation (passing reference images for style/character consistency), codex supports `-i, --image <FILE>...` to attach images to the prompt context.

### THE BUG: greedy `-i` parse eats your prompt

The `-i FILE...` flag is **variadic-greedy** — without termination it consumes the prompt itself as another `<FILE>` argument and codex falls through to stdin, which is empty, and errors out:

```
Reading prompt from stdin...
No prompt provided via stdin.
```

**WRONG (silently fails):**
```bash
codex exec [opts] -i ref1.png -i ref2.png "prompt text" > log 2>&1
```

**RIGHT (use `--` separator):**
```bash
codex exec [opts] -i ref1.png -i ref2.png -- "prompt text" > log 2>&1
```

The `--` terminates the `-i` flag's greedy parse and the prompt is correctly passed as a positional argument. This is the single most important pattern for any multi-reference image-gen workflow.

### Sequential reference chaining for series consistency

When generating a series of frames where each new frame must reference the previous one (key frames of a video sequence, multi-shot scenes, character continuity across beats), chain codex calls with `&&` so each call waits for the previous output to materialize before starting:

```bash
mkdir -p output/dir && \
  codex exec [opts] -i char_sheet.png \
    -- "frame1 prompt → save to output/dir/frame1.png" > /tmp/log1 2>&1 && \
  codex exec [opts] -i char_sheet.png -i output/dir/frame1.png \
    -- "frame2 prompt → save to output/dir/frame2.png" > /tmp/log2 2>&1 && \
  codex exec [opts] -i char_sheet.png -i output/dir/frame1.png -i output/dir/frame2.png \
    -- "frame3 prompt → save to output/dir/frame3.png" > /tmp/log3 2>&1
```

This guarantees temporal/visual continuity: frame N has frame N-1 (and earlier) loaded as visual references. Each frame's prompt explicitly tells codex which attached image is the "character bible" vs the "previous frame" so the model knows what to match.

Run the whole chain as ONE background bash call (`run_in_background: true`) — you get a single notification when the entire chain completes. Per-frame failures stop the chain via `&&` short-circuit.

### Parallel non-dependent generation

For independent assets with NO continuity needed (e.g., 5 different characters in 5 different scenes), use **5 separate background bash calls in a single message** instead of chaining — much faster (5x parallel rather than serial).

### Reference image hierarchy (recommended pattern)

For viral content, character drama, multi-shot work: build a reusable reference hierarchy. Three levels:

1. **Character bible (turnaround sheet)** — 3-pose model sheet on white background, locks body / material / proportion / wardrobe. The canonical reference for ALL downstream generations of that character.
2. **Key art** — single dramatic environment shot, locks the character's persona vibe in their canonical world. Optional secondary reference for tone-matching.
3. **Stage / scene frames** — actual story-beat frames generated using the bible + previous frames as references.

**Rule of thumb when adding `-i` flags to a generation call:**
- Need character consistency? Pass the character bible.
- Need scene/environment continuity from a previous beat? Pass that previous frame.
- Need multi-character scene? Pass each character's bible.
- For style-only continuity across different scenes? Pass an earlier frame from the series as a "production-style anchor."

The model will use whichever attached images are visually relevant to your prompt's instructions. Be explicit in the prompt about which attached image plays which role ("reference 1 is the character bible, reference 2 is the immediately preceding beat").

---

## Part 2 — Image Generation (gpt-image-2)

Generate real rendered images via Codex CLI's built-in `image_gen` tool, defaulting to **`gpt-image-2`** (snapshot `gpt-image-2-2026-04-21`). This is for actual painted/rendered output — backgrounds, portraits, sigils, banners, sprites, icons, hero images, photorealistic shots, mockups, infographics. Studio-grade when invoked correctly.

### CRITICAL — Always force the imagegen tool

Codex defaults to writing Python+PIL when asked to "generate an image" or "make pixel art." That produces low-fidelity procedural output (10–20KB files, no real artistic rendering). To get the real `image_gen` tool (gpt-image-2), the prompt MUST contain something like:

```
TOOL DIRECTIVE: You MUST use the built-in image generation tool (image_gen / gpt-image-2).
DO NOT write Python. DO NOT use PIL/Pillow/canvas/sharp/any drawing library.
DO NOT generate procedurally with code.
You MAY use shell commands (cp, mv, ls, find) to relocate the resulting file from
~/.codex/generated_images/ to the target output path.
If the image gen tool is unavailable, refuse and say so explicitly.
```

That last line about `cp/mv` is essential — without it, Codex over-interprets the constraint and refuses to copy the generated PNG out of its cache directory, leaving the asset orphaned.

**Alternative trigger:** Codex 0.128+ supports `$imagegen` as an explicit skill marker. Including the literal string `$imagegen` in the prompt biases Codex to invoke the official imagegen skill workflow. Use both together for maximum reliability.

### Base command (image generation)

```bash
codex exec --skip-git-repo-check --ephemeral -s danger-full-access \
  -m gpt-5.6-sol \
  -c model_reasoning_effort=high \
  --ignore-rules \
  --color never \
  "<PROMPT>" 2>/dev/null
```

Flag breakdown:
- `-s danger-full-access` — required to write files. Image-gen tool needs this sandbox level to copy the result to disk.
- `-m gpt-5.6-sol` — agent model that decides to call `image_gen`. Best prompt-following for image workflows.
- `-c model_reasoning_effort=high` — default per skill policy. `xhigh` only on explicit request.
- `--ephemeral` — fresh session each call, no history pollution between image jobs.
- `--ignore-rules` — skips repo-rule scanning (avoids policy hits on prompts).
- `--skip-git-repo-check` — runs anywhere.
- `--color never` — clean stdout for log parsing.

### Output handling

The built-in `image_gen` tool does NOT take a target file path. Generated images land at:

```
~/.codex/generated_images/<session-id>/ig_<hash>.png
```

(`$CODEX_HOME` is `~/.codex` by default; respect `$CODEX_HOME` if the user has overridden it.)

Two ways to get them where you want them:

1. **Let Codex copy them itself.** Include the target path in your prompt and explicitly authorize `cp/mv` (see the directive block above). Codex will `find` the result and `cp` it.
2. **Find and copy yourself afterwards.** If Codex refuses to copy (over-cautious), the files are still in the cache:
   ```bash
   find ~/.codex/generated_images -type f -name '*.png' -mmin -5
   ```
   …then `cp` them to where you need them. This is the reliable fallback.

### Parallelization (default for ≥2 assets)

For multiple assets, fire each as a separate `codex exec` Bash call with `run_in_background: true`. Don't serialize — Codex sessions are independent.

```
Single message with 4 Bash tool calls, all run_in_background: true:
  codex exec [...flags...] "PROMPT_BG"        > /tmp/codex-bg.log 2>&1
  codex exec [...flags...] "PROMPT_PORTRAITS" > /tmp/codex-portraits.log 2>&1
  codex exec [...flags...] "PROMPT_SIGIL"     > /tmp/codex-sigil.log 2>&1
  codex exec [...flags...] "PROMPT_BANNER"    > /tmp/codex-banner.log 2>&1
```

After each completes, inspect the log to confirm the image-gen tool was invoked (look for `ig_<hash>.png` in the log — that's the cache path indicator) and confirm the target file exists.

**Default rule:** if generating ≥2 distinct assets, always parallelize. ONE prompt per `codex exec` call — do not stuff multiple unrelated assets into a single prompt; quality drops and recovery is harder.

**Note on `n`:** the underlying API supports `n` (1–10) for **variants of the same prompt**. Don't use `n` as a substitute for separate prompts when you want different assets — that's what parallel `codex exec` calls are for.

### Sizes (gpt-image-2)

`gpt-image-2` accepts `auto` or any `WIDTHxHEIGHT` that meets ALL of:

- Max edge ≤ **3840px**
- Both edges multiples of **16px**
- Long-edge / short-edge ratio ≤ **3:1**
- Total pixels between **655,360** and **8,294,400**
- Outputs above **2560×1440** are technically supported but flagged as experimental — quality variance is higher

Popular sizes (use these unless there's a reason not to):

| Use | Size |
|---|---|
| Square (default fast) | `1024x1024` |
| Landscape | `1536x1024` |
| Portrait | `1024x1536` |
| 2K square | `2048x2048` |
| 2K landscape (widescreen) | `2048x1152` |
| 4K landscape | `3840x2160` |
| 4K portrait | `2160x3840` |
| Auto | `auto` |

Square is fastest. Don't ask for tiny output (e.g. `256x256`) — the tool will reject it (below min-pixels). Generate at a supported size and downscale with `sips` afterwards.

### Quality (gpt-image-2)

Four levels: `low`, `medium`, `high`, `auto`.

- `low` — fast drafts, thumbnails, candidate sweeps, "show me the rough idea"
- `medium` — fine for most preview/draft work
- `high` — **default for finals.** Final assets, dense text inside the image, tight composition, identity-sensitive edits, large outputs
- `auto` — let the model pick

The built-in tool doesn't expose `--quality` directly to the prompt, but you can ask for it ("high quality, fine detail") and the tool tends to honor it. For deterministic quality control, use the CLI fallback (see below).

### Prompt craft (gpt-image-2)

The OpenAI prompting guide is explicit: **structure prompts as scene/backdrop → subject → key details → constraints**, and state intended use to set polish level. gpt-image-2 rewards specificity in this rough order:

1. **Use case / intended surface** — "landing page hero," "tarot card icon," "game faction crest," "infographic frame"
2. **Subject + composition** — what's centered, what's around it, camera angle
3. **Material / medium** — "obsidian shard," "bronze cupped hands," "filigree gold ornament," "matte ceramic," "35mm film"
4. **Lighting / mood** — "deep amber inner glow," "cold sapphire light bleeding from cracks," "soft studio softbox"
5. **Style anchor** — "Octopath Traveler / Triangle Strategy / Disco Elysium portrait icon caliber" — these references work consistently. For photoreal: avoid "studio polish" language; prompt as if capturing a real moment.
6. **Palette** — give hex codes when colors matter: `warm orange (#ff6a3d), sapphire (#4a8eff), jade (#3dd47b)`
7. **Negative space** — "leave the upper third calm for UI overlay readability"
8. **Background instruction** — "deep midnight starfield" / "flat #00ff00 chroma-key for removal" / "warm sunset gradient"
9. **Constraints / avoid list** — "no text, no watermark, no logos" / for edits: "change only X; keep Y unchanged"

For game-asset icons / sigils: ask for "tarot card icon" or "videogame faction crest" — these style references reliably produce iconic centered compositions with ornate frames.

For atmospheric backgrounds: cinematic + painterly + name a specific game or visual ref. Avoid "pure pixel art" — you'll get blocky low-fi. Instead: "high-fidelity digital painting in the visual language of detailed pixel art" gets you the polished JRPG-screenshot look.

For text inside the image (gpt-image-2 is strong at this): put the literal text in **straight quotes**, specify font style and placement, and use `quality: high`. For tricky words: spell letter-by-letter and demand verbatim rendering.

### Transparency — chroma-key workflow (preferred)

`gpt-image-2` does NOT support `background=transparent`. The official Codex skill ships a workflow that's just as good for most subjects:

1. Generate the subject on a flat solid chroma-key background (default `#00ff00`; use `#ff00ff` for green subjects; avoid `#0000ff` for blue subjects).
2. Run the bundled helper to convert the key color to alpha.

**The bundled helper is at:**

```
$CODEX_HOME/skills/.system/imagegen/scripts/remove_chroma_key.py
```

(typically `~/.codex/skills/.system/imagegen/scripts/remove_chroma_key.py`)

Standard invocation:

```bash
python "${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/scripts/remove_chroma_key.py" \
  --input <source-from-cache>.png \
  --out <final-with-alpha>.png \
  --auto-key border \
  --soft-matte \
  --transparent-threshold 12 \
  --opaque-threshold 220 \
  --despill
```

Prompt the chroma-key generation like this (paste into your `codex exec` prompt):

```
Create the requested subject on a perfectly flat solid #00ff00 chroma-key background for background removal.
The background must be one uniform color with no shadows, gradients, texture, reflections, floor plane, or lighting variation.
Keep the subject fully separated from the background with crisp edges and generous padding.
Do not use #00ff00 anywhere in the subject.
No cast shadow, no contact shadow, no reflection, no watermark, and no text unless explicitly requested.
```

If a thin fringe remains after removal, retry once with `--edge-contract 1`. Use `--edge-feather 0.25` only when the edge is visibly stair-stepped and the subject is not shiny/reflective.

**When to escalate to true alpha (`gpt-image-1.5`):** hair, fur, feathers, smoke, glass, liquids, translucent materials, reflective objects, soft shadows, realistic product grounding, or subject colors that conflict with all practical key colors. **Always ask the user first** before falling back to `gpt-image-1.5` — it's a model downgrade and requires `OPENAI_API_KEY`.

### CLI fallback — when to use it

There's an official bundled CLI at `~/.codex/skills/.system/imagegen/scripts/image_gen.py` (defaults: `gpt-image-2`, `--size auto`, `--quality medium`, `--output-format png`). Use it when:

- The user explicitly asks for "the CLI" or "the image gen API"
- You need true transparency (`gpt-image-1.5 --background transparent --output-format png`) — confirm with user first
- You have a large batch (>10 assets) and want to drive it from a JSONL file via `generate-batch`
- You need explicit `--quality`, `--size`, `--output-format`, `--mask`, or `--background` control beyond what the prompt can coax out of the built-in tool
- You're editing a local image file with masks (the built-in `image_gen` edit path needs the image already in the conversation context; CLI takes `--image <path>` and `--mask <path>` directly)

**This requires `OPENAI_API_KEY`** (the built-in tool uses the Codex subscription). Switching to API pricing also bypasses the 3–5× usage-limit multiplier — useful for high-volume work.

Setup:

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export IMAGE_GEN="$CODEX_HOME/skills/.system/imagegen/scripts/image_gen.py"
```

Quick generate:

```bash
python "$IMAGE_GEN" generate \
  --prompt "A cozy alpine cabin at dawn" \
  --size 1024x1024 \
  --quality high \
  --out output/imagegen/alpine-cabin.png
```

Edit:

```bash
python "$IMAGE_GEN" edit \
  --image input.png \
  --prompt "Replace only the background with a warm sunset" \
  --quality high \
  --out output/imagegen/sunset-edit.png
```

True transparency (only after user confirms):

```bash
python "$IMAGE_GEN" generate \
  --model gpt-image-1.5 \
  --prompt "A clean product cutout on a transparent background" \
  --background transparent \
  --output-format png \
  --out output/imagegen/product-cutout.png
```

**Never modify `image_gen.py`.** It's bundled and updated by Codex; changes get clobbered. If something seems missing, ask the user.

**Subcommands:** `generate`, `edit`, `generate-batch`. `--dry-run` prints the API payload without calling the API or needing the key.

### Common failures and fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Tiny PNG (5–20KB), looks like procedural pixel grid | Codex went the Python/PIL path | Add the TOOL DIRECTIVE block + `$imagegen` marker; re-fire |
| "I generated it but couldn't save to that path" | Codex refused `cp` because directive said "no drawing library" too strictly | Add `You MAY use shell commands (cp, mv) to relocate` to the directive |
| Image saved but green/checker background instead of transparent | Expected — gpt-image-2 doesn't do native alpha. You asked for transparency. | Run the chroma-key helper at `~/.codex/skills/.system/imagegen/scripts/remove_chroma_key.py` |
| Empty cache directory after run | Codex refused or errored silently | Check the log file (`/tmp/codex-X.log`) — image gen may have hit content policy or rate limit |
| Wrong aspect ratio | Tool didn't honor exact dimensions | Re-prompt with one of the popular sizes (`1024x1024`, `1536x1024`, etc.); crop with `sips` if needed |
| Multiple assets in one prompt — only some land on disk | Codex generated all but only copied first | Split into separate `codex exec` calls (recommended). Don't use `n` for distinct assets — `n` is for variants of one prompt |
| "size must be auto or WIDTHxHEIGHT, multiples of 16" error from CLI | Bad size for gpt-image-2 | Both edges must be multiples of 16, total pixels in [655,360 .. 8,294,400], aspect ≤ 3:1, max edge ≤ 3840 |
| "transparent backgrounds are not supported in gpt-image-2" | Tried `--background transparent` with default model | Either chroma-key workflow, or `--model gpt-image-1.5 --background transparent --output-format png` (after user confirms) |
| `input_fidelity` errors | gpt-image-2 doesn't accept it | Drop the flag — gpt-image-2 always uses high fidelity for image inputs |

### End-to-end template (single asset, built-in tool)

```bash
codex exec --skip-git-repo-check --ephemeral -s danger-full-access \
  -m gpt-5.6-sol \
  -c model_reasoning_effort=high \
  --ignore-rules \
  --color never \
  "\$imagegen
TOOL DIRECTIVE: You MUST use the built-in image generation tool (image_gen / gpt-image-2). DO NOT write Python. DO NOT use PIL/Pillow/canvas/sharp/any drawing library. DO NOT generate procedurally with code. You MAY use shell commands (cp, mv, ls, find) to relocate the resulting file from ~/.codex/generated_images/ to the target output path. If the image gen tool is unavailable, refuse explicitly.

Generate one image, save to <ABSOLUTE_TARGET_PATH>. Size: 1024x1024.

Use case: <product-mockup | ui-mockup | illustration-story | stylized-concept | photorealistic-natural | etc>
Subject: <SUBJECT>.
Composition: <COMPOSITION>.
Style: <STYLE_REFERENCE>.
Lighting/mood: <LIGHTING>.
Palette: <PALETTE_HEXES>.
Background: <BG_INSTRUCTION>.
Constraints: no text, no watermark, no logos.

Use the image generation tool. Save the PNG to the path above." \
  > /tmp/codex-asset.log 2>&1
```

(Note: the `$imagegen` marker is escaped as `\$imagegen` inside the bash double-quoted string so the shell doesn't try to expand it as a variable.)

### End-to-end template (parallel batch, built-in tool)

```bash
# Fire N jobs in parallel — one prompt per call
codex exec [...flags...] "PROMPT_BG"        > /tmp/codex-bg.log 2>&1 &
codex exec [...flags...] "PROMPT_PORTRAITS" > /tmp/codex-portraits.log 2>&1 &
codex exec [...flags...] "PROMPT_SIGIL"     > /tmp/codex-sigil.log 2>&1 &
codex exec [...flags...] "PROMPT_BANNER"    > /tmp/codex-banner.log 2>&1 &
wait

# If any didn't land in target path, recover from cache:
find ~/.codex/generated_images -type f -name '*.png' -mmin -10
# View candidates, then `cp` to target paths.
```

In an agent harness, the equivalent is to invoke each `codex exec` via Bash with `run_in_background: true`, then proceed with other work. You'll be notified per completion. Inspect each log to confirm the tool path was taken (look for `ig_<hash>.png` in the log) and confirm the target file exists.

### End-to-end template (CLI fallback, batch from JSONL)

For high-volume work where you want explicit control + API pricing:

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export IMAGE_GEN="$CODEX_HOME/skills/.system/imagegen/scripts/image_gen.py"
export OPENAI_API_KEY="<key>"

# JSONL: one job per line, each with prompt + size + quality + out
cat > tmp/imagegen/jobs.jsonl <<'EOF'
{"prompt":"alpine cabin at dawn","size":"1536x1024","quality":"high","out":"output/imagegen/cabin.png"}
{"prompt":"forest path in mist","size":"1536x1024","quality":"high","out":"output/imagegen/forest.png"}
{"prompt":"coastal cliff at sunset","size":"1536x1024","quality":"high","out":"output/imagegen/coast.png"}
EOF

python "$IMAGE_GEN" generate-batch \
  --jobs tmp/imagegen/jobs.jsonl \
  --concurrency 5
```

`--dry-run` to preview payloads without spending. Defaults: model `gpt-image-2`, concurrency 5, max 500 jobs per batch.

### Quality bar / acceptance check

After generation, always:

1. `ls -la <target>` — confirm file is **>100KB** (real renders are typically 700KB–2.3MB at `medium`, 1–4MB at `high`; tiny files = procedural fallback).
2. View the PNG visually before declaring success — confirm composition matches the prompt.
3. If any asset is off, re-fire **that single prompt** with tightened wording rather than re-running the whole batch.

### Known limits

- **No native alpha** in gpt-image-2 — chroma-key workflow with the bundled helper is the default; `gpt-image-1.5` CLI fallback only after user confirms.
- **Text rendering** is much improved (~99% accuracy across scripts) but still: quote literal text, specify font/placement, use `quality: high` for dense or small text.
- **Content policy** applies — same as ChatGPT. Faces, gore, explicit violence, identifiable real people will be refused or sanitized.
- **One asset per prompt** — don't chain multiple unrelated assets into one prompt; quality drops and recovery is harder. Use parallel `codex exec` calls.
- **`input_fidelity` is fixed high** in gpt-image-2 — don't try to set it.
- **Cost awareness** — image-gen turns burn Codex limits 3–5× faster than text turns. If the user flags rate limits, switch to `OPENAI_API_KEY` + CLI fallback (API pricing). Reference per-image API cost: low ~$0.011–0.017, medium ~$0.042–0.063, high ~$0.165–0.211 (1024×1024 / 1024×1536).

---

## Part 3 — Fleets (parallel multi-lane orchestration)

A **fleet** is N `codex exec` delegates working at once. Each lane is a plain background `codex exec` process. This is pure local orchestration — you (the orchestrator agent) spawn the lanes, hand each a self-contained brief, watch their logs, and integrate their output. No control plane required.

### Operator defaults for delegate lanes

| Setting | Default | Why |
|---|---|---|
| Model | `gpt-5.6-sol` (`-m gpt-5.6-sol`) | The fleet workhorse. Never silently downgrade. |
| Reasoning | `high` (`-c model_reasoning_effort=high`) | `xhigh` for genuinely hard lanes (gnarly refactors, debugging); `medium` for grunt/mechanical lanes. |
| Sandbox | `--full-auto` for write lanes; `--sandbox read-only` for read/review lanes | Write lanes need to edit their claimed files. Only grant what the lane needs. |
| Working dir | `-C <lane dir>` | Anchor each lane in its claimed directory or worktree. |

### Spawn recipe (one lane)

```bash
caffeinate -i codex exec --skip-git-repo-check --full-auto \
  -C <LANE_DIR> \
  -m gpt-5.6-sol \
  -c model_reasoning_effort=high \
  "<SELF-CONTAINED LANE BRIEF>" > /tmp/lane-A.log 2>&1
```

Fire it with `run_in_background: true`. The brief is the lane's **entire contract** — it must state the goal, the exact files the lane OWNS, the files it must NOT touch (and which sibling owns them), the acceptance check, and how to report done/failed. A delegate can't see your conversation; everything it needs goes in the brief.

> **`caffeinate -i` (macOS).** A lid-close or idle sleep silently kills a mid-flight lane (you'll see ~5KB of output, zero edits). Wrap every spawn in `caffeinate -i` so the machine stays awake for the fleet. A respawn with the same brief is safe when `git status` shows no partial work.

### Fleet patterns (3–20 lanes)

- **Stagger the spawns** (2–5s apart): firing every lane's first model call simultaneously is a thundering herd. In a live 23-lane run, 2 lanes wedged on dead connections at startup and sat silent for 30 minutes. The stagger costs a minute; a zombie costs half an hour.
- **Real ceiling ≈ 20 concurrent `codex exec` processes** — that's RAM + OpenAI rate limits, not orchestration. Beyond that, tier and queue.
- **Tier the lanes**: quick read/explore lanes → `medium` read-only; standard write lanes → `high` full-auto; deep refactor / gnarly debugging / review-gate lanes → `xhigh`.
- **Read lanes stay read-only**: give review/analysis lanes `--sandbox read-only` so they physically cannot edit. Escalate to a write lane if edits are needed — don't tell a read lane to patch.
- **Liveness check from the surface side**: a codex lane whose log file hasn't grown for many minutes with zero tool calls is dead regardless of the process table. Respawn it with the same brief.
- **Completions are claims, not evidence.** "Succeeded" from a lane means it *thinks* it's done. Run the lane's acceptance check yourself (targeted typecheck / lint / tests in its dir) before integrating.

### Concurrent WRITE lanes — worktree isolation (the key trick)

When multiple lanes must WRITE to the same repo at once, they'll clobber each other's saves in a shared checkout. Two proven shapes:

**A. Worktree-per-lane + one commit per lane + orchestrator cherry-picks** (best for lanes carving disjoint regions of the SAME file, or any risk of live collisions):

```bash
# Per lane, at a pinned base commit:
git worktree add --detach ../fleet-lane-A <BASE_SHA>
# (install deps / build as needed inside the worktree)
# Spawn the lane with -C ../fleet-lane-A ; brief tells it to make ONE commit when done.
# Orchestrator then cherry-picks each lane's commit onto main in completion order,
# gating (build+typecheck+test) at each pick.
```

No live collisions, linear history with each lane's commit preserved, orchestrator gates every pick. Prove the mechanics on a baseline worktree whose gate is GREEN before any lane spawns. Conflicts concentrate in append zones (import blocks, guard-list arrays) and resolve as unions; for moved code, resolve by OWNERSHIP — grep the lane's target file for the moved decl before deleting anything.

**B. Shared tree with explicit OWNS / DO-NOT-TOUCH lists** (works when lanes touch clearly disjoint files):

- Each lane brief carries an explicit OWNS list and a DO-NOT-TOUCH list naming which sibling owns what. Lanes then self-report fouls ("sibling edits present, left intact") instead of "fixing" them.
- **Shared files (barrels, CLI entry, validators) are declared append-only.** Allocate each shared file to exactly one commit at integration time.
- **Lanes never run the repo-root gate or git** — targeted tests + per-package typecheck only. The orchestrator runs the single full gate (test+typecheck+build) after ALL lanes settle, repairs cross-lane breakage (expect ~1–2 pinned-literal test failures when one lane reshapes source another lane's test pins), then commits per coherent unit.
- **A lane adding shared exports can break every other lane's build mid-flight.** If one lane edits a barrel/type file everyone imports, rebuild that package (`<your build for that package>`) so downstream lanes resolve. For long fleets, run a quiet rebuild loop (~every 2 min) so the outage window stays bounded.

### What makes a fleet run good

- The brief embeds the full contract: goal, OWNS, DO-NOT-TOUCH (+ sibling owner), acceptance check, and report format. The delegate follows the brief verbatim — put everything in it.
- **Re-verify "already fixed" claims live.** A lane that verifies a fix only against an in-memory/demo store has verified nothing — FK ordering, contention, and real-data edge cases exist only against the real backend.
- **Honest failure beats a cheerful lie.** A lane reporting "failed: sibling's mid-flight edit broke cross-package typecheck" is often fine — read the failure note; "outside my lane" usually means integrate normally and verify at the gate.
- **Expect other work on the machine.** Only act on your own fleet's lanes/logs; never reap processes you didn't spawn without inspecting them first.

---

## Credits

Merged and maintained by **Avenox** — [avenox.lol](https://avenox.lol). This is a distilled, dependency-free build of an internal Codex operations skill. Feedback and improvements welcome.
