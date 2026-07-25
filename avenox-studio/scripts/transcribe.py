#!/usr/bin/env python3
"""
transcribe.py — local Turkish transcription via mlx-whisper (Apple Silicon).
Usage: python3 transcribe.py INPUT.mp4 OUTPREFIX
  -> writes transcript/OUTPREFIX_timed.json  (segments with start/end/text)
     and    transcript/OUTPREFIX_narration.txt (plain text)
"""
import os, sys, json, time, certifi

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

import mlx_whisper

IN = sys.argv[1]
PREFIX = sys.argv[2] if len(sys.argv) > 2 else "out"
OUTDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "transcript")
os.makedirs(OUTDIR, exist_ok=True)

print(f"transcribe başlıyor (turbo, tr, timestamp'li): {os.path.basename(IN)}", flush=True)
t0 = time.time()
r = mlx_whisper.transcribe(
    IN,
    path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
    language="tr",
    word_timestamps=False,
)
segs = [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip()}
        for s in r["segments"]]
dur_min = segs[-1]["end"] / 60 if segs else 0

with open(os.path.join(OUTDIR, f"{PREFIX}_timed.json"), "w") as f:
    json.dump({"text": r["text"].strip(), "segments": segs}, f, ensure_ascii=False, indent=1)
with open(os.path.join(OUTDIR, f"{PREFIX}_narration.txt"), "w") as f:
    f.write(r["text"].strip() + "\n")

print(f"OK · segment:{len(segs)} · içerik:{dur_min:.1f}dk · işlem:{time.time()-t0:.0f}sn", flush=True)
print(f"kaydedildi: {PREFIX}_timed.json + {PREFIX}_narration.txt", flush=True)
