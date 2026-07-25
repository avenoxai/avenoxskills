---
name: avenox-video
description: >
  Avenox Studio — local-first YouTube video production pipeline (ROUTER, read first). Use for ANY
  request to edit, cut, produce, assemble, caption, score, or render a long-form video, or to make
  motion graphics for one. Wraps open-source tooling (auto-editor, mlx-whisper, MLT/melt, ffmpeg)
  plus HyperFrames for animated graphics. Triggers: "edit this video", "cut the recording",
  "make graphics", "extract captions", "render the final", a job name, or anything about the
  video pipeline. The human is director/quality gate; the agent is the operator.
---

# Avenox Studio — operator router

The fast operator guide for a **local-first, agent-operated video pipeline**.
Everything runs on your own machine: no cloud editor, no upload-to-render.

**The human directs and approves quality; the agent runs the pipeline.**

## Setup

```bash
export STUDIO_JOBS="$HOME/video/projects"   # heavy media lives here
export STUDIO_ROOT="/path/to/this/repo"     # scripts, templates, brand
```

Requirements: macOS (hardware encode via `h264_videotoolbox`; Apple Silicon for
`mlx-whisper`), `ffmpeg`, `python3`, `melt`/MLT, Node (for HyperFrames). Most
of this works on Linux with `libx264` and a CUDA whisper build substituted in.

## Operating principles

1. **Media discipline.** Heavy media NEVER in a cloud-synced folder — sync will
   thrash on multi-GB intermediates and can corrupt in-flight writes. Jobs live
   in `$STUDIO_JOBS/<job>/` (`raw/ cut/ graphics/ audio/ outputs/`). Your notes
   system holds only the brain: this system, the brand spec, `edit.json` plans.
2. **Director loop.** Produce a **preview** (graphics stills + a fast draft
   render) → send for notes → only then final render. Never ship a final
   without sign-off. This is the single most important rule; an agent that
   renders finals unreviewed will burn hours on a rejected cut.
3. **Brand is a hard constraint, not a suggestion.** Read `brand/frame.md`
   before making any graphic. Define it once and lock it. (The reference
   implementation is deliberately anti-"AI slop": premium editorial, warm paper
   + ink + a single accent, no neon/gradient/glassmorphism/3D-gloss.)
4. **Format:** YouTube 16:9 1080p60. Preset in `brand/presets/youtube-16x9.json`.
5. **Finishing is hybrid.** Auto-generate the draft; the same `.mlt` opens in
   Kdenlive or Shotcut for hand-finishing. Don't try to automate taste.
6. **Transcription defaults to LOCAL** `mlx-whisper` with
   `whisper-large-v3-turbo` — fast, free, and strong on non-English audio. Note
   that most LLM-routing proxies expose no whisper endpoint; if you go remote,
   use a dedicated speech API.

## Scripts (`scripts/`)

| Script | Does |
|---|---|
| `autocut.sh IN.mp4 [balanced\|aggressive\|conservative]` | silence-cut → `_cut.xml` (Premiere) or `--export` variants |
| `transcribe.py IN.mp4 PREFIX` | → `transcript/PREFIX_timed.json` + `_narration.txt` |
| `mltgen.py edit.json out.mlt --base <job-dir>` | edit-list → MLT project (Kdenlive/Shotcut/melt) |
| `vrender.sh project.mlt out.mp4 [fast\|quality]` | render (fast = HW draft, quality = CRF18 master) |
| `grabshot.sh` | clipboard screenshot → disk |
| `slides2png.sh` | legacy static slides — prefer HyperFrames |
| `remove-silence.py` | standalone silence pass |

## The 7 steps

1. **Intake** — copy raw → `$STUDIO_JOBS/<job>/raw/`. Confirm the brief and
   which segments actually matter.
2. **Rough cut** — `autocut.sh raw.mov balanced` → `cut/screen_cut.mp4`;
   `transcribe.py` for the script. Full recipe → `avenox-roughcut` skill.
3. **Graphics** — HyperFrames. Route via the `hyperframes` skill → usually
   `motion-graphics` (short beats), `faceless-explainer` (concept stretches),
   or `general-video`. Read `brand/frame.md` first; render animated **MP4**s
   into `graphics/`. Full recipe → `avenox-graphics` skill.
4. **Assemble** — write `edit.json` (template in `templates/edit.json`) mixing
   `cut/*.mp4` + `graphics/*.mp4` + music → `mltgen.py edit.json project.mlt
   --base <job-dir>`.
5. **Captions** — `transcribe.py` → `.srt`; apply `brand/caption-corrections.json`
   (copy it from `caption-corrections.example.json` — a find/replace map for terms
   your ASR reliably mangles). Ship as YouTube CC, not burned-in.
6. **Music** — bed under everything, sidechain-duck under voice, target
   ~-14 LUFS. Track attribution in `CREDITS.md`.
7. **Export** — `vrender.sh project.mlt draft.mp4 fast` → **director review** →
   `vrender.sh … final.mp4 quality` → prune scratch files.

## Graphics quality bar

HyperFrames clips must obey `brand/frame.md`. Prefer type-driven, restrained,
weighty motion. If a beat doesn't need motion, a clean static frame is fine —
don't animate for the sake of animating.

## Reference

- Rough cut: `avenox-roughcut` · Graphics: `avenox-graphics`
- HyperFrames skills: `hyperframes` (router), `hyperframes-cli`,
  `hyperframes-animation`, `hyperframes-creative`, `motion-graphics`,
  `faceless-explainer`, `general-video`
- Brand spec: `brand/frame.md` (fill in from `brand/frame.template.md`)
