#!/bin/bash
# slides2png.sh — render a reveal.js deck to per-slide PNGs via decktape (headless Chrome).
# Usage: slides2png.sh DECK.html OUTDIR [WIDTHxHEIGHT]
# Produces OUTDIR/slide_001.png ... (final state per slide, no fragment steps).
set -e
DECK="$1"; OUT="${2:-slides_png}"; SIZE="${3:-1920x1080}"
mkdir -p "$OUT"
npx -y decktape reveal \
  --no-fragments \
  --screenshots --screenshots-directory "$OUT" \
  --screenshots-size "$SIZE" --screenshots-format png \
  "$DECK" "$OUT/_deck.pdf"
echo "slides -> $OUT/"
