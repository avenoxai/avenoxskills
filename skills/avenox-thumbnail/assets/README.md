# Assets — bring your own

This skill ships **no image binaries**, on purpose:

- **Mascot references** are channel identity. Yours should live here, not
  someone else's.
- **Brand logos** (OpenAI, Anthropic, DeepSeek, …) are third-party trademarks.
  Redistributing them in a public repo is a licensing problem, so this repo
  ships the *fetch recipe* instead of the files.

## What to put here

```
assets/
  mascot-ref.png          # canonical, neutral expression — passed as -i on EVERY job
  mascot-ref-<variant>.png # optional: angry / shocked / celebrating variants
  logos/
    <tool>.png            # fetched via references/logo-library.md
```

### Mascot reference requirements

- Square-ish, transparent or flat plain background
- Full body, neutral/default expression, clean edges
- Under ~2MB — larger buys nothing and slows every job
- One canonical file. If you keep variants, they must be visibly the *same
  character*, not redraws.

If you don't have a mascot yet, generate one with the `codex-fleet` skill,
then pick a single output as canonical and never regenerate it — every future
thumbnail keys off this one file.

### Logos

Fetch with the recipe in `references/logo-library.md` (Simple Icons +
`qlmanage` rasterization). Check each brand's trademark policy before
publishing covers that use it; most permit editorial/reference use of an
unmodified mark.
