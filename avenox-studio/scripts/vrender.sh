#!/bin/bash
# vrender.sh — render an MLT project to MP4 with melt (headless, no GUI).
# Usage: vrender.sh PROJECT.mlt [OUT.mp4] [fast|quality]
#   quality (default) = libx264 CRF 18, slow   (crisp master, good for code/text)
#   fast              = h264_videotoolbox       (Apple Silicon HW, ~4x faster)
set -e
MELT="$(command -v melt || echo /Applications/kdenlive.app/Contents/MacOS/melt)"
PROJ="$1"; OUT="${2:-out.mp4}"; MODE="${3:-quality}"
[ -x "$MELT" ] || { echo "melt not found (install: brew install mlt)"; exit 1; }
if [ "$MODE" = "fast" ]; then
  "$MELT" "$PROJ" -consumer avformat:"$OUT" \
    vcodec=h264_videotoolbox b=14M acodec=aac ab=256k pix_fmt=yuv420p
else
  "$MELT" "$PROJ" -consumer avformat:"$OUT" \
    vcodec=libx264 crf=18 preset=slow acodec=aac ab=256k pix_fmt=yuv420p
fi
echo "rendered: $OUT"
