"""Assemble the United Front video v4.
- 20 clips joined with 0.8s crossfade dissolves (xfade).
- Narration (voice 4, speed 90) placed at the computed visual section starts.
- Chinese subtitles burned in (SRT) at the bottom.
- Background music: 'Echoes in the Archive' by Sascha Ende (CC BY 4.0),
  looped, mixed well below the narration.
- Audio fade in 0.6s / fade out 1.0s.
Output: ~/workspace/video-united-front/united_front_video_v4.mp4
"""
import os, subprocess

BASE = os.path.expanduser("~/workspace/video-united-front")
CLIPS = os.path.join(BASE, "clips2")
NARR = os.path.join(BASE, "narration")
SRT = os.path.join(BASE, "subtitles.ass")
MUSIC = os.path.join(BASE, "music/echoes_in_the_archive.mp3")
OUT = os.path.join(BASE, "united_front_video_v12.mp4")

ORDER = ["title_open", "A1", "A2", "A3", "B1", "B2", "B3",
         "C1", "C2", "C3", "C4", "C5", "D1", "D2", "D3", "D4",
         "E1", "E2", "E3", "title_close"]
DURS = {"title_open": 10.0,
        "A1": 17.9, "A2": 17.9, "A3": 17.7,
        "B1": 19.3, "B2": 12.0, "B3": 26.6,
        "C1": 15.5, "C2": 15.5, "C3": 15.5, "C4": 15.5, "C5": 15.3,
        "D1": 13.1, "D2": 13.1, "D3": 13.1, "D4": 13.1,
        "E1": 15.7, "E2": 15.7, "E3": 15.6,
        "title_close": 16.0}
XF = 0.8

def clip_start(idx):
    return sum(DURS[n] for n in ORDER[:idx]) - idx * XF

SEC_START = {L: clip_start(i) for L, i in
             [("A", 1), ("B", 4), ("C", 7), ("D", 12), ("E", 16)]}
TOTAL = sum(DURS[n] for n in ORDER) - (len(ORDER) - 1) * XF
print("section starts (s):", {k: round(v, 1) for k, v in SEC_START.items()})
print(f"total video: {TOTAL:.1f}s")

# ---- inputs: 20 video clips + 5 narration mp3s + music (looped) ----
inputs = []
for name in ORDER:
    inputs += ["-i", os.path.join(CLIPS, name + ".mp4")]
for L in "ABCDE":
    inputs += ["-i", os.path.join(NARR, f"sec_{L}.mp3")]
inputs += ["-stream_loop", "-1", "-i", MUSIC]   # index 25

# ---- video filter: xfade chain ----
parts = []
prev = "0:v"
acc_dur = DURS[ORDER[0]]
for i in range(1, len(ORDER)):
    off = clip_start(i)
    label = f"xf{i}"
    parts.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[{label}]")
    prev = label
    acc_dur = acc_dur + DURS[ORDER[i]] - XF
parts.append(f"[{prev}]ass='{SRT}'[vout]")

# ---- audio filter: delay each narration to its section start, mix, pad, fade ----
a_parts = []
for j, L in enumerate("ABCDE"):
    idx = 20 + j
    ms = int(round(SEC_START[L] * 1000))
    a_parts.append(f"[{idx}:a]adelay={ms}|{ms}[a{L}]")
a_parts.append("[aA][aB][aC][aD][aE]amix=inputs=5:normalize=0[amix]")
a_parts.append(f"[amix]apad,atrim=0:{TOTAL:.3f},afade=t=in:st=0:d=0.6,afade=t=out:st={TOTAL-1.0:.3f}:d=1.0[narr]")
# background music: DYNAMIC (v9) — louder where there is no narration, quiet
# under the voice so it stays clear.
#   opening title (0-9.2s, no voice): 0.25, ducking to 0.15 as narration starts
#   narration (9.2-280.3s): 0.15
#   after the last voice line ends (280.3s): swell 0.15 -> 0.40 over 2s,
#   holding 0.40 through the closing title so the ending lands, then the
#   usual 3s fade-out. NARR_END = E start (238.3) + E narration (42.0s).
NARR_END = SEC_START["E"] + 42.0
A0 = SEC_START["A"]
_vol = (f"if(lt(t,{A0:.1f}),0.25,"
        f"if(lt(t,{A0+2:.1f}),0.25-0.10*(t-{A0:.1f})/2,"
        f"if(lt(t,{NARR_END:.1f}),0.15,"
        f"if(lt(t,{NARR_END+2:.1f}),0.15+0.25*(t-{NARR_END:.1f})/2,0.40))))")
a_parts.append(f"[25:a]atrim=0:{TOTAL:.3f},volume='{_vol}':eval=frame,afade=t=in:st=0:d=2.0,afade=t=out:st={TOTAL-3.0:.3f}:d=3.0[mus]")
a_parts.append("[narr][mus]amix=inputs=2:normalize=0[aout]")

fc = ";".join(parts + a_parts)
cmd = (["ffmpeg", "-y", "-v", "error"] + inputs +
       ["-filter_complex", fc,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
        "-c:a", "libmp3lame", "-b:a", "192k",
        "-movflags", "+faststart", OUT])
print("running ffmpeg ...")
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr[-3000:])
    raise SystemExit("ffmpeg failed")
print("ASSEMBLED ->", OUT)
