# Prompt template — codex gpt-image-2

The proven command (via the `codex-fleet` skill). Fire each concept as a
separate `run_in_background: true` Bash call, all in one message.

## Command skeleton

```bash
OUT="${THUMB_OUT:-$HOME/Desktop/thumbnails}"
SK="<this skill>/assets"
mkdir -p "$OUT"

codex exec --skip-git-repo-check --ephemeral -s danger-full-access \
  -m gpt-5.6-sol -c model_reasoning_effort=high --ignore-rules --color never \
  -i "$SK/mascot-ref.png" -i "$SK/logos/<tool>.png" -- "\$imagegen
TOOL DIRECTIVE: You MUST use the built-in image generation tool (image_gen / gpt-image-2). DO NOT write Python/PIL/canvas. You MAY use shell (cp, mv, find) to relocate from ~/.codex/generated_images/ to the target path. If unavailable, refuse explicitly.
Generate ONE YouTube thumbnail 1280x720. Save to $OUT/<name>.png (cp/find). High quality.
Reference 1 is the CHANNEL MASCOT: <one-line on-model description from references/character-and-safety.md>. Keep EXACTLY on-model; <expression/pose — arms bent, NO straight raised arm>.
Reference 2 is the <TOOL> logo (<distinguishing description>).
CONCEPT (<one-line idea>): <composition — subject on RIGHT, what's around, focal element>.
STYLE: modern high-CTR, <accent-color> background, crisp cut-out mascot, high contrast, clean, 3 elements.
TEXT (verbatim, MASSIVE heavy sans-serif caps, LEFT, black outline): '<WORD1>' white on top, '<WORD2>' bright <ACCENT> below. <HOOK_LANG> exact: <spell letter-by-letter if non-ASCII>. No other text, no watermark. Keep LOWER-RIGHT clear.
Use the image generation tool now. Save to the path above." > /tmp/<name>.log 2>&1
```

## Critical mechanics (learned the hard way)

- **`-i <img> … -- "prompt"`** — the `--` is REQUIRED. Without it Codex's greedy
  `-i` parse swallows the prompt and fails on empty stdin. Pass the mascot ref
  first, then logos, then `--`, then the prompt.
- **`\$imagegen`** — escape the `$` inside the double-quoted bash string.
- Always include the **TOOL DIRECTIVE** block, or Codex writes a low-fidelity
  Python/PIL image instead of calling the real image tool. Also grant the
  `cp`/`find` permission or it won't move the file out of
  `~/.codex/generated_images/`.
- **Size:** ask for `1280x720` (YouTube native, 16:9, both edges divisible by
  16). gpt-image-2 sometimes returns a near-miss size (e.g. 1672×941) — fix at
  delivery with `sips -z 720 1280 <file>`.
- **Non-Latin / diacritic text:** gpt-image-2 renders extended Latin
  (İ Ş Ğ Ü Ö Ç, Ł Ą Ż, Å Ä Ö …) correctly ~99% of the time, but **spell each
  hook letter-by-letter in the prompt and demand verbatim output**. If a
  diacritic comes out wrong, re-fire that ONE job — it self-corrects on retry.
  Watch for confusable pairs (dotted `İ` vs dotless `I`, breve vs caron,
  cedilla vs comma-below).
- **ASR caveat** for transcript-derived copy: whisper-family models reliably
  mishear product names ("Claude" → "Cloud", "CLAUDE.md" → "Cloud.md",
  version numbers → nonsense). Correct these before baking text into an image.

## Output handling

- The prompt tells Codex to `cp` the result to `$OUT/<name>.png`. If it refuses
  or misses, recover from cache:
  ```bash
  find ~/.codex/generated_images -type f -name '*.png' -mmin -10
  ```
- After the batch: `md5 -r "$OUT"/*.png | sort` and eyeball for duplicates.
  Re-fire any duplicate solo — parallel jobs occasionally collide.

## Service tier

Standard tier, per the `codex-fleet` default — **do not add `-c service_tier=fast`**.
A thumbnail batch is N parallel background jobs; nobody is blocked on any single
lane's latency, so fast buys ~1.5x speed at ~2.5x rate cost for no wall-clock
gain. Opt in per-call only if you are actively waiting on one foreground cover.

## Parallel discipline

- N concepts = N background calls in ONE message. They don't contend.
- If a job hangs beyond ~15 min with no image hash in its log, it's stuck
  retrying text rendering — kill it (`pkill -f "<name>"`) and re-fire with
  simpler wording or a shorter hook.
