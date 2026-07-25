#!/bin/bash
# ───────────────────────────────────────────────
# Avenox AutoCut — sessizlik kesici (auto-editor wrapper)
# Sessiz alanları bulur, keser, Premiere'e import edilebilir XML üretir.
# Video RE-RENDER edilmez; sadece kesim listesi (XML) çıkar.
#
# Kullanım:
#   ./autocut.sh "video.mp4"              # denge modu (varsayılan)
#   ./autocut.sh "video.mp4" agresif      # boşlukları sıkı kes
#   ./autocut.sh "video.mp4" koruyucu     # ≤15 sn sessizlikleri KORU (demo/tutorial için)
#   ./autocut.sh "video.mp4" 0.8% 3s      # elle: threshold + margin
#
# Çıktı: video_cut.xml  →  Premiere'de File > Import ile aç.
# ───────────────────────────────────────────────
set -e
AE="$HOME/Desktop/videoassets/auto-editor"
IN="$1"

if [ -z "$IN" ] || [ ! -f "$IN" ]; then
  echo "❌ Dosya yok. Kullanım: autocut.sh <video> [agresif|denge|koruyucu | threshold% margin]"
  exit 1
fi

# Preset veya elle ayar
case "$2" in
  agresif)   THRESH="0.6%"; MARGIN="0.4s" ;;
  ""|denge)  THRESH="0.6%"; MARGIN="2s" ;;
  koruyucu)  THRESH="0.6%"; MARGIN="7.5s" ;;   # ≤15sn boşlukları korur
  *)         THRESH="$2"; MARGIN="${3:-2s}" ;;  # elle: $2=threshold, $3=margin
esac

OUT="${IN%.*}_cut.xml"
echo "🎬 Kesiliyor:  $(basename "$IN")"
echo "   threshold=$THRESH  margin=$MARGIN"
"$AE" "$IN" --edit "audio:threshold=$THRESH" --margin "$MARGIN" --export premiere -o "$OUT"
echo ""
echo "✅ Hazır: $OUT"
echo "   → Premiere: File > Import → bu XML'i seç → medyayı orijinal videoya relink et."
