"""Build an ASS subtitle file with EXPLICIT bottom positioning.
libass's MarginV proved unreliable (subtitles alternated between bottom
and middle), so every event carries a \\pos tag pinning it to the bottom.
Two lines, bottom line baseline at y=690 (720p), so the block sits at the
very bottom and never jumps."""
import re, os, sys

# Allow running from either the original Linux workspace or the current directory
DEFAULT_BASE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.expanduser("~/workspace/video-united-front")
if not os.path.exists(BASE):
    BASE = DEFAULT_BASE

SRT = os.path.join(BASE, "subtitles.srt")
OUT = os.path.join(BASE, "subtitles.ass")

# Font size: default reduced by 3 sizes (72 -> 66 -> 60 -> 54pt), or pass as CLI arg
# Options:
#   72pt: original v11 doubled size
#   60pt: reduced by 2 sizes (PPT standard 72 -> 66 -> 60)
#   54pt: reduced by 3 sizes (PPT standard 72 -> 66 -> 60 -> 54, optimal balance)
#   48pt: typographic scale down 2 tiers (72 -> 60 -> 48)
FONT_SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 54

def srt_ts_to_ass(ts):
    # 00:00:09,050 -> 0:00:09.05
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return f"{int(h)}:{m}:{s}.{ms[:2]}"

events = []
cur = {}
for line in open(SRT, encoding="utf-8"):
    line = line.rstrip("\n")
    if line.strip().isdigit() and not cur:
        cur = {"idx": line}
    elif "-->" in line and cur and "start" not in cur:
        a, b = line.split(" --> ")
        cur["start"] = srt_ts_to_ass(a.strip())
        cur["end"] = srt_ts_to_ass(b.strip())
    elif line.strip() == "" and cur and "start" in cur:
        events.append(cur); cur = {}
    elif cur and "start" in cur:
        cur.setdefault("text", []).append(line)
if cur and "start" in cur:
    events.append(cur)

header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Serif CJK SC,{FONT_SIZE},&HFFFFFF,&HFFFFFF,&H000000,&H000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
with open(OUT, "w", encoding="utf-8") as f:
    f.write(header)
    for e in events:
        txt = "\\N".join(e["text"])
        # \\pos pins the whole 2-line block: centre x=640, bottom line near y=690
        f.write(f"Dialogue: 0,{e['start']},{e['end']},Default,,0,0,0,,{{\\pos(640,690)}}{txt}\n")
print(f"Wrote {len(events)} events -> {OUT}")
