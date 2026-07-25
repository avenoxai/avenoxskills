---
name: avenox-roughcut
description: >
  Avenox Studio — transcript-driven rough cut (silence + flub/retake removal).
  Use when cutting a raw talking-head or screen recording: remove dead air AND bad takes/restarts.
  Proven recipe with real gotchas baked in. Triggers: "rough cut", "cut the silences",
  "remove flubs/retakes", a raw screen recording to trim. Part of avenox-video step 2.
---

# Rough cut — transcript-driven (silence + flubs)

Two kinds of cut: **silence** (dead air, mechanical → auto-editor) and
**flubs/retakes** (a restarted sentence, semantic → transcript + agent
judgment). The director approves the flub list before anything is cut.

## Pipeline

Job dir (LOCAL — never inside a synced/cloud folder):
`$STUDIO_JOBS/<job>/{raw,cut,transcript,frames}`

> Set `STUDIO_JOBS` to wherever you keep heavy media, e.g.
> `export STUDIO_JOBS=~/video/projects`. Keeping media out of a synced folder
> matters: cloud sync will thrash on multi-GB intermediates.

### 1. Transcribe (local mlx-whisper — Apple Silicon)

```bash
cd "$STUDIO_JOBS/<job>"
python3 -c "
import os, certifi; os.environ['SSL_CERT_FILE']=certifi.where(); os.environ['REQUESTS_CA_BUNDLE']=certifi.where()
import mlx_whisper, json
r=mlx_whisper.transcribe('<RAW>', path_or_hf_repo='mlx-community/whisper-large-v3-turbo', language='<LANG>', word_timestamps=False)
segs=[{'i':i,'start':round(s['start'],2),'end':round(s['end'],2),'text':s['text'].strip()} for i,s in enumerate(r['segments'])]
json.dump({'text':r['text'].strip(),'segments':segs}, open('transcript/raw_timed.json','w'), ensure_ascii=False, indent=1)
"
```

~48s for 14 min of audio on an M-series Mac. Local is the default — it is
faster and cheaper than any API round trip at this length. Note that most
LLM-routing proxies have **no** whisper endpoint; if you must go remote, use a
dedicated speech API.

### 2. Detect flubs (read transcript, propose to the director)

Scan `raw_timed.json` for:

- repeated sentence-starts (the same opening said twice)
- cut-off restarts (a half sentence, then the full take)
- self-corrections ("we need X" → "instead of X, …")
- hanging filler words right before a gap

Present as a table (`mm:ss` + text). **The director approves before cutting.**
This step stays human-gated — an agent cutting semantic content unreviewed
will eventually remove a real point.

### 3. Cut — flubs (ffmpeg) THEN silence (auto-editor)

Order matters: flub timecodes are in RAW coordinates, so cut flubs **first**;
silence removal shifts the timeline underneath them.

**Flubs via ffmpeg `select`** (frame-precise; build KEEP as the complement of
the cut ranges):

```bash
KEEP="between(t,4.96,46.16)+between(t,48.98,69.42)+...+between(t,LAST,99999)"
ffmpeg -y -i "<RAW>" \
  -vf "select='$KEEP',setpts=N/FRAME_RATE/TB" \
  -af "aselect='$KEEP',asetpts=N/SR/TB" \
  -c:v h264_videotoolbox -b:v 18M -c:a aac -b:a 256k cut/flubcut.mp4
```

**Silence via auto-editor:**

```bash
export SSL_CERT_FILE="$(python3 -c 'import certifi;print(certifi.where())')"; export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
python3 -m auto_editor cut/flubcut.mp4 --edit "audio:threshold=8%" --margin 0.5s \
  -c:v h264_videotoolbox -b:v 16M --no-open -o cut/draft_v1.mp4
```

## Gotchas (learned the hard way — do not rediscover)

- **auto-editor needs the certifi SSL fix** or its binary download fails with
  `CERTIFICATE_VERIFY_FAILED`. Always export `SSL_CERT_FILE` first.
- **Do NOT use auto-editor `--cut-out` for flubs.** In v29 a multi-range
  `--cut-out a,b c,d …` leaks the last range as a positional input file
  ("Could not open input file"). Use the ffmpeg `select` filter for content
  cuts — it is also frame-precise, where auto-editor's cuts are coarser.
- **Pause length is `--margin`, not `--threshold`.** `0.15s` ≈ very tight
  (~0.3s pauses); `0.5s` ≈ ~1s max pauses, which reads as flowy rather than
  clipped. Tune margin for rhythm, leave threshold alone.
- **`threshold=8%` is calibrated to one specific voice/mic.** Re-calibrate for
  your own setup: too low clips soft word-endings, too high leaves dead air.
- The auto-editor binary is a WyattBlue release, auto-downloaded by the pip
  wrapper into its own cache.

## Output & next

- Render the draft with hardware encoding (`h264_videotoolbox`) for fast
  review; produce the master later via `mltgen`/`.mlt`, or a single-pass
  keep-list at `libx264 CRF 18`.
- After cutting, **re-transcribe the cut** (or remap timecodes) so graphics
  land accurately → hand to the `avenox-video` graphics step.
- Show the director the draft. They are the quality gate.
