#!/usr/bin/env python3
"""
mltgen.py — turn a simple JSON edit-list into an MLT XML project (.mlt).

The .mlt it produces opens directly in Kdenlive / Shotcut for human polish AND
renders headlessly with `melt project.mlt -consumer avformat:out.mp4 ...`.

This is the "Claude drives the editor" bridge: I describe the timeline in JSON
(seconds, human-friendly), this emits frame-accurate MLT XML.

Edit-list schema (JSON):
{
  "profile": "atsc_1080p_60",        # MLT profile name (fps/size live here)
  "fps": 60, "width": 1920, "height": 1080,
  "video": [                          # ordered segments on the video track
    {"type": "clip",  "file": "screen_cut.mp4", "in": 0.0, "out": 35.2},
    {"type": "slide", "file": "img/slide_01.png", "dur": 6.0},
    {"type": "clip",  "file": "screen_cut.mp4", "in": 35.2, "out": 80.0}
  ],
  "audio": {"file": "music.mp3", "gain": 0.15},   # OPTIONAL bed under everything
  "title": "<Job Title> — edit"
}

Usage:
  python3 mltgen.py edit.json out.mlt
  python3 mltgen.py edit.json out.mlt --base "$STUDIO_JOBS/<job>"
Paths in the edit-list are resolved against --base (default: edit.json's dir),
then written as ABSOLUTE paths so melt/Kdenlive find them from anywhere.
"""
import json, os, sys, html, argparse

def sec_to_frames(sec, fps):
    return max(0, int(round(float(sec) * fps)))

def esc(s):
    return html.escape(str(s), quote=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("editlist")
    ap.add_argument("out")
    ap.add_argument("--base", default=None, help="root for resolving relative paths")
    args = ap.parse_args()

    with open(args.editlist) as f:
        ed = json.load(f)

    base = args.base or os.path.dirname(os.path.abspath(args.editlist))
    def resolve(p):
        return p if os.path.isabs(p) else os.path.abspath(os.path.join(base, p))

    fps    = ed.get("fps", 60)
    width  = ed.get("width", 1920)
    height = ed.get("height", 1080)
    profile = ed.get("profile", "atsc_1080p_60")
    title  = ed.get("title", "Claude edit")

    producers = []          # (id, resource, extra_props_dict)
    entries   = []          # (producer_id, in_frame, out_frame)
    pid = 0

    for seg in ed.get("video", []):
        res = resolve(seg["file"])
        if not os.path.exists(res):
            print(f"WARN: missing file {res}", file=sys.stderr)
        if seg["type"] == "slide":
            n = sec_to_frames(seg.get("dur", 5.0), fps)
            # image producer: length must cover the shown duration
            producers.append((f"p{pid}", res, {"length": str(n + 1)}))
            entries.append((f"p{pid}", 0, max(0, n - 1)))
        elif seg["type"] == "clip":
            inf  = sec_to_frames(seg["in"], fps)
            outf = sec_to_frames(seg["out"], fps) - 1
            if outf < inf:
                outf = inf
            producers.append((f"p{pid}", res, {}))
            entries.append((f"p{pid}", inf, outf))
        else:
            print(f"WARN: unknown segment type {seg['type']}", file=sys.stderr)
            pid += 1
            continue
        pid += 1

    total_frames = sum(o - i + 1 for _, i, o in entries)

    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>')
    L.append(f'<mlt LC_NUMERIC="C" version="7.0.0" title="{esc(title)}" profile="{esc(profile)}">')
    L.append(f'  <profile description="{esc(profile)}" width="{width}" height="{height}" '
             f'progressive="1" sample_aspect_num="1" sample_aspect_den="1" '
             f'display_aspect_num="16" display_aspect_den="9" '
             f'frame_rate_num="{fps}" frame_rate_den="1" colorspace="709"/>')

    # video producers
    for pid_, res, extra in producers:
        L.append(f'  <producer id="{pid_}">')
        L.append(f'    <property name="resource">{esc(res)}</property>')
        for k, v in extra.items():
            L.append(f'    <property name="{esc(k)}">{esc(v)}</property>')
        L.append('  </producer>')

    # video playlist
    L.append('  <playlist id="video_track">')
    for pid_, inf, outf in entries:
        L.append(f'    <entry producer="{pid_}" in="{inf}" out="{outf}"/>')
    L.append('  </playlist>')

    # optional audio bed
    has_audio = bool(ed.get("audio"))
    if has_audio:
        a = ed["audio"]
        ares = resolve(a["file"])
        L.append('  <producer id="audio0">')
        L.append(f'    <property name="resource">{esc(ares)}</property>')
        L.append('  </producer>')
        L.append('  <playlist id="audio_track">')
        L.append(f'    <entry producer="audio0" in="0" out="{max(0,total_frames-1)}"/>')
        L.append('  </playlist>')

    # tractor wires the tracks together
    L.append('  <tractor id="tractor0" title="{}">'.format(esc(title)))
    L.append('    <track producer="video_track"/>')
    if has_audio:
        gain = ed["audio"].get("gain", 1.0)
        L.append('    <track producer="audio_track" hide="video"/>')
        # lower the music bed
        L.append('    <filter id="vol0">')
        L.append('      <property name="mlt_service">volume</property>')
        L.append(f'      <property name="gain">{gain}</property>')
        L.append('      <property name="track">1</property>')
        L.append('    </filter>')
    L.append('  </tractor>')
    L.append('</mlt>')

    with open(args.out, "w") as f:
        f.write("\n".join(L) + "\n")

    secs = total_frames / fps if fps else 0
    print(f"wrote {args.out}  ·  {len(entries)} segments  ·  {total_frames} frames  ·  ~{secs:.1f}s @ {fps}fps")
    if has_audio:
        print(f"  + audio bed: {ed['audio']['file']} (gain {ed['audio'].get('gain',1.0)})")

if __name__ == "__main__":
    main()
