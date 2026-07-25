---
name: avenox-graphics
description: >
  Avenox Studio — produce brand-locked motion graphics with HyperFrames and composite them onto a
  cut video. Use when making cutaway/overlay graphics: title cards, diagrams, data-viz, loops,
  lower-thirds, outro. Proven cutaway + composite recipe with gotchas. Triggers: "make graphics",
  "add an animation", "motion graphic", "intro/outro card", "data-viz". Part of avenox-video step 3.
---

# Graphics — HyperFrames cutaways → composite

Brand source of truth: `brand/frame.md`. Define it once, then never deviate
inside a job. (Reference implementation: warm paper `#f3efe4`, ink `#1b1712`,
one golden accent `#e8b23a`, a serif display face + a grotesk UI face, plus a
mascot. Deliberately **anti-AI-slop** — no neon, no gradient mesh, no
glassmorphism, no 3D gloss.)

## Pipeline

1. **Project:** `cd "$STUDIO_JOBS/<job>/graphics" && npx hyperframes init gfx`
   (one-time; installs a headless chromium — slow first run, background it).
2. **One composition per beat** = a standalone `<name>.html`. Reuse the brand
   template below. Each is full-screen 1920×1080 — a **cutaway** (opaque,
   replaces footage) or a transparent **overlay**.
3. **Render serially** (render reads `index.html`):
   ```bash
   for f in *.html; do
     n="${f%.html}"; [ "$n" = index ] && continue
     cp "$f" index.html
     npx hyperframes render -f 60 --resolution landscape -o "renders/$n.mp4"
   done
   ```
4. **Composite** all cutaways onto the cut via ffmpeg, each at its timecode.

## Composition contract (HyperFrames)

- `#root` with `data-composition-id="main" data-start data-duration data-width data-height`.
- Every timed element: `class="clip"` + `data-start data-duration data-track-index`.
- ONE paused GSAP timeline registered:
  `window.__timelines["main"] = gsap.timeline({paused:true})`.
  HyperFrames seeks it per frame, so everything must be **seek-safe**: use
  `fromTo`/`set`, and position every tween on `tl`.
- **Deterministic only** — no `Date.now()`, no `Math.random()`, no runtime
  fetch. Web fonts via `<link>` are fine.
- Render flags: `-f 60`, `--resolution landscape` (1920×1080), `--format mp4`
  (use `mov`/`webm` for alpha overlays).

## Brand template

- Fonts via a single `<link>` to your webfont provider — renders fine in
  headless chrome.
- `html,body{background:<paper>}` + a paper div, radial vignette, and an SVG
  `feTurbulence` grain at `opacity .05` / `mix-blend-mode: multiply`. **Fix the
  turbulence seed** or the grain is nondeterministic and frames will flicker.
- Kicker (grotesk, tracked caps) → title (serif, heavy) → accent underline
  (`scaleX` wipe) → mascot (`assets/mascot.png`).

## Mascot transparency (keying a mascot off an ivory plate)

HSV key — saturated body colors and black ink survive, low-saturation cream
becomes alpha:

```python
import numpy as np
from PIL import Image
im = Image.open(src).convert('RGB')
a  = np.asarray(im) / 255.
mx = a.max(2)
s  = np.where(mx > 1e-6, (mx - a.min(2)) / np.maximum(mx, 1e-6), 0)
bg = (s < 0.22) & (mx > 0.60)
out = np.dstack([np.asarray(im), np.where(bg, 0, 255).astype('uint8')])
img = Image.fromarray(out, 'RGBA')
img.crop(img.getbbox()).save(dst)
```

Tune `0.22` / `0.60` to your plate. Too aggressive and you eat highlights on
the subject.

## Compositing cutaways onto the cut

Per cutaway input:
`[i:v]setpts=PTS+{START}/TB,format=yuv420p[ovi]`, then
`[prev][ovi]overlay=enable='between(t,{START},{END})':eof_action=pass[vi]`.

Keep the base audio (`-map 0:a`). Hardware encode with
`h264_videotoolbox -b:v 18M`.

## Gotchas

- **npx/hyperframes need the SSL cert fix:**
  `export SSL_CERT_FILE=$(python3 -c 'import certifi;print(certifi.where())')`
  (and `REQUESTS_CA_BUNDLE`) or downloads fail.
- `hyperframes init` first run is slow (chromium download) — background it.
- **Blended is the better default.** Prefer animated **overlays on the live
  screen** (lower-thirds, kinetic titles, callouts — rendered transparent as
  `.mov`/`.webm` with `--format mov`) for most beats. Reserve **full-screen
  cutaways** for the intro, outro, and genuine dead zones where the screen
  shows nothing useful. Replacing a screen that has useful content loses
  information — overlay it instead.
- **Placement:** grab the frame at the target timecode (`ffmpeg -ss`), look at
  it, and place graphics in empty safe zones — never over a face or important
  UI. Optional: HyperFrames `remove-background` matting to sit graphics behind
  the subject.
- **Don't over-animate.** Restraint reads as premium; constant motion reads as
  a template.
- Render time scales with frame count — keep cutaways short (5–26s). Long
  sustained pieces get expensive fast.
