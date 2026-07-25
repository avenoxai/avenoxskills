#!/usr/bin/env python3
"""Klasik boşluk silme — ffmpeg silencedetect ile sessiz aralıkları kesip
konuşma parçalarını birleştirir (A/V senkron korunur, tek re-encode).

Kullanım:
  python3 remove-silence.py <input.mp4> [output.mp4] [--db -30] [--min 0.6] [--pad 0.12]
"""
import subprocess, sys, re, os

inp = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else os.path.splitext(inp)[0] + "-cut.mp4"
def arg(flag, default):
    return float(sys.argv[sys.argv.index(flag)+1]) if flag in sys.argv else default
NOISE = arg("--db", -30.0)      # sessizlik eşiği dB
MIN_SIL = arg("--min", 0.6)    # bu süreden uzun sessizlikler kesilir (sn)
PAD = arg("--pad", 0.12)       # konuşmanın kenarına bırakılan tampon (sn)

dur = float(subprocess.check_output(["ffprobe","-v","error","-show_entries",
    "format=duration","-of","csv=p=0",inp]).decode().strip())

print(f"silencedetect (noise={NOISE}dB, d={MIN_SIL}s)...", flush=True)
p = subprocess.run(["ffmpeg","-i",inp,"-af",f"silencedetect=noise={NOISE}dB:d={MIN_SIL}",
    "-f","null","-"], stderr=subprocess.PIPE, text=True)
log = p.stderr
sils = []
cur = None
for line in log.splitlines():
    m = re.search(r"silence_start:\s*([-\d.]+)", line)
    if m: cur = float(m.group(1))
    m = re.search(r"silence_end:\s*([-\d.]+)", line)
    if m and cur is not None:
        sils.append((cur, float(m.group(1)))); cur = None

# sessizliklerin tümleyeni = tutulacak (konuşma) parçalar, tampon ile
keeps = []
pos = 0.0
for s, e in sils:
    ks, ke = pos, s
    if ke - ks > 0.05:
        keeps.append([max(0, ks - PAD), min(dur, ke + PAD)])
    pos = e
if dur - pos > 0.05:
    keeps.append([max(0, pos - PAD), dur])
# üst üste binenleri birleştir
merged = []
for k in keeps:
    if merged and k[0] <= merged[-1][1]:
        merged[-1][1] = max(merged[-1][1], k[1])
    else:
        merged.append(k)
keeps = [k for k in merged if k[1]-k[0] > 0.10]

kept = sum(k[1]-k[0] for k in keeps)
print(f"{len(sils)} sessiz aralık, {len(keeps)} konuşma parçası. "
      f"{dur:.1f}s -> {kept:.1f}s ({100*(1-kept/dur):.0f}% kesildi)", flush=True)
if not keeps:
    print("kesilecek bir şey yok"); sys.exit(0)

# filter_complex script üret (trim+atrim+concat, tek re-encode)
fc = []
for i,(s,e) in enumerate(keeps):
    fc.append(f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[v{i}];")
    fc.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}];")
fc.append("".join(f"[v{i}][a{i}]" for i in range(len(keeps))) + f"concat=n={len(keeps)}:v=1:a=1[v][a]")
fcpath = "/tmp/rs_filter.txt"
open(fcpath,"w").write("".join(fc))

print("re-encode...", flush=True)
r = subprocess.run(["ffmpeg","-y","-v","error","-stats","-i",inp,
    "-filter_complex_script",fcpath,"-map","[v]","-map","[a]",
    "-c:v","libx264","-preset","veryfast","-crf","20","-c:a","aac","-b:a","192k",out])
if r.returncode==0:
    nd=float(subprocess.check_output(["ffprobe","-v","error","-show_entries",
        "format=duration","-of","csv=p=0",out]).decode().strip())
    print(f"\nBITTI: {nd/60:.1f} dk · {os.path.getsize(out)/1e6:.0f} MB · {out}")
else:
    print("HATA: ffmpeg exit", r.returncode)
