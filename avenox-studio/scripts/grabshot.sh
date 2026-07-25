#!/bin/bash
# Grab the image currently on the macOS clipboard -> save to img/screenshots/ with a timestamp.
# Usage: grabshot.sh [optional-name]
DIR="${STUDIO_JOBS:-$HOME/video/projects}/img/screenshots"
mkdir -p "$DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
NAME="${1:-shot_$STAMP}"
OUT="$DIR/${NAME}.png"
osascript <<OSA >/dev/null 2>&1
set outFile to POSIX file "$OUT"
try
    set pngData to (the clipboard as «class PNGf»)
on error
    return "NO_IMAGE"
end try
set fh to open for access outFile with write permission
set eof fh to 0
write pngData to fh
close access fh
return "OK"
OSA
if [ -s "$OUT" ]; then echo "saved: $OUT ($(du -h "$OUT" | cut -f1))"; else rm -f "$OUT"; echo "no image on clipboard — did you copy a screenshot?"; fi
