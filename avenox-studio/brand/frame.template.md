# Brand frame — TEMPLATE

Copy to `frame.md` and fill in. Every graphic in this pipeline is checked
against this file. **Lock it early**: the cost of deviating mid-channel is
higher than the cost of a slightly imperfect first choice, because visual
consistency is what makes a thumbnail recognizable in a crowded feed.

## Palette

| Role | Hex | Notes |
|---|---|---|
| Paper / background | `#______` | the base surface everything sits on |
| Ink / text | `#______` | near-black, not pure `#000` |
| Accent (ONE) | `#______` | used sparingly — underlines, highlights, one word |
| Alert / negative | `#______` | optional |

One accent. Two accents is already a different brand.

## Type

- **Display / titles:** `____________` — weight `___`
- **UI / kickers:** `____________` — weights `___`
- **Mono (code):** `____________`

## Texture

- Grain: SVG `feTurbulence`, opacity `0.05`, `mix-blend-mode: multiply`,
  **fixed seed** (nondeterministic grain flickers across rendered frames).
- Vignette: radial, subtle.

## Mascot / identity mark

- Reference image: `brand/mascot.png`
- On-model contract: ______________________________________________
- Never: ______________________________________________

## Anti-patterns (the "not this" list)

Write down what your brand is explicitly *not*. This list does more work than
the palette. Reference implementation bans:

- neon on black
- gradient meshes / "aurora" backgrounds
- glassmorphism, frosted panels
- 3D glossy plastic renders
- stock-photo people at laptops
- centered everything with no hierarchy

## Format

- Delivery: 16:9, 1920×1080, 60fps
- Preset: `brand/presets/youtube-16x9.json`
