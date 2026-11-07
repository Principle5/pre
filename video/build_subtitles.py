"""Build an SRT subtitle file for the United Front video v2.
Sentence timing inside each narration section is proportional to character
count (TTS pace is steady enough for subtitles). Section start offsets are
computed from the clip list + 0.8s crossfades between consecutive clips.
"""
import re, subprocess, os

BASE = os.path.expanduser("~/workspace/video-united-front")
NARR = os.path.join(BASE, "narration")
OUT = os.path.join(BASE, "subtitles.srt")

# clip durations in order (must match render_clips_v2.py JOBS + title cards)
CLIPS = [
    ("title_open", 10.0),
    ("A1", 17.9), ("A2", 17.9), ("A3", 17.7),
    ("B1", 19.3), ("B2", 19.3), ("B3", 19.3),
    ("C1", 15.5), ("C2", 15.5), ("C3", 15.5), ("C4", 15.5), ("C5", 15.3),
    ("D1", 13.1), ("D2", 13.1), ("D3", 13.1), ("D4", 13.1),
    ("E1", 15.7), ("E2", 15.7), ("E3", 15.6),
    ("title_close", 16.0),
]
XF = 0.8  # crossfade seconds between consecutive clips

def clip_start(idx):
    """Start time of clip idx in the final (crossfaded) video."""
    return sum(d for _, d in CLIPS[:idx]) - idx * XF

# section -> first clip index
SEC_CLIP = {"A": 1, "B": 4, "C": 7, "D": 12, "E": 16}

def narr_dur(letter):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0",
                        os.path.join(NARR, f"sec_{letter}.mp3")],
                       capture_output=True, text=True)
    return float(r.stdout.strip())

def srt_ts(sec):
    sec = max(0.0, sec)
    h = int(sec // 3600); m = int((sec % 3600) // 60)
    s = int(sec % 60); ms = int(round((sec - int(sec)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def wrap_sentence(s, limit=24):
    """Split every sentence into exactly two display lines, so the subtitle
    block is always the same height and never jumps up/down between 1-line
    and 2-line cards. Break at a comma/、/； near the middle.
    IMPORTANT: always prefer a comma break over splitting mid-sentence —
    a mid split can tear a 2-char word apart (e.g. 生活 -> 生|活), which
    reads badly. So: any comma beats any mid split, even an unbalanced one.
    Returns the text with an SRT \\N break."""
    mid = len(s) // 2
    cands = [i for i, ch in enumerate(s) if ch in "，、；"]
    if cands:
        # prefer commas in the middle band, else any comma (closest to mid)
        lo, hi = int(len(s) * 0.25), int(len(s) * 0.75)
        inband = [i for i in cands if lo <= i <= hi]
        pool = inband if inband else cands
        i = min(pool, key=lambda x: abs(x - mid))
        return s[:i + 1] + "\\N" + s[i + 1:]
    # no comma at all: split near the middle (Chinese has no spaces;
    # unavoidable for a punctuation-less sentence)
    if len(s) <= 4:
        return s  # too short to split meaningfully; keep 1 line
    return s[:mid] + "\\N" + s[mid:]

def sentences(text):
    t = re.sub(r"\[[^\]]*\]", "", text)
    t = re.sub(r"\s+", " ", t).strip()
    return [s.strip() for s in re.split(r"(?<=[。！？；])", t) if s.strip()]

entries = []  # (start, end, text)
for L in "ABCDE":
    text = open(os.path.join(NARR, f"sec_{L}.txt"), encoding="utf-8").read()
    sents = sentences(text)
    dur = narr_dur(L)
    total_chars = sum(len(s) for s in sents)
    offset = clip_start(SEC_CLIP[L])
    t = 0.0
    for s in sents:
        d = dur * len(s) / total_chars
        start = offset + t
        end = offset + t + d
        entries.append((start, end, wrap_sentence(s)))
        t += d

# write SRT; give each line a tiny lead-in (0.15s) so it reads as on-time
with open(OUT, "w", encoding="utf-8") as f:
    for i, (st, en, txt) in enumerate(entries, 1):
        f.write(f"{i}\n{srt_ts(st - 0.15)} --> {srt_ts(en - 0.05)}\n{txt}\n\n")

print(f"Wrote {len(entries)} subtitle lines -> {OUT}")
for st, en, txt in entries[:3]:
    print(f"  {srt_ts(st)} --> {srt_ts(en)}  {txt[:30]}")
print("  ...")
for st, en, txt in entries[-2:]:
    print(f"  {srt_ts(st)} --> {srt_ts(en)}  {txt[:30]}")
total = sum(d for _, d in CLIPS) - (len(CLIPS) - 1) * XF
print(f"final video duration (with xfades): {total:.1f}s")
