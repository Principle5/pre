"""Cut real archival footage (public domain, US War Dept 'The Battle of
China' 1944, archive.org) into 1280x720 clips matching the video's
segment durations, with the same Song-style caption as the photo clips."""
import os, subprocess
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.expanduser("~/workspace/video-united-front")
SRC = os.path.join(BASE, "footage/battle_of_china_512kb.mp4")
CLIPS = os.path.join(BASE, "clips2")
SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"
W, H = 1280, 720

def caption_overlay(text):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    f = ImageFont.truetype(SERIF, 36)
    bbox = d.textbbox((0, 0), text, font=f)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    x, y = 36, 36
    d.rounded_rectangle([x-16, y-12, x+tw+18, y+th+16], radius=8, fill=(0, 0, 0, 110))
    d.text((x, y), text, font=f, fill=(245, 240, 228, 255))
    return ov

# (clip name, source start, duration, caption)
JOBS = [
    # A2: Dec 9th Movement — street crowd (students take to the streets)
    ("A2", 1370.0, 17.9, "一二·九运动 · 1935年12月"),
    # C2: Burma Road — the famous switchback mountain road (real footage)
    ("C2", 2810.0, 15.5, "滇缅公路 · 1937年"),
    # D4: civilians crossing a bridge — people in the rear area (v7)
    ("D4", 1970.0, 13.1, "大后方 · 1940年代"),
]

for name, start, dur, cap in JOBS:
    # 1) cut + scale/crop the 4:3 footage to 1280x720 (fill, centre-crop)
    tmp = os.path.join(CLIPS, f"{name}_footage_raw.mp4")
    subprocess.run(["ffmpeg","-y","-v","error","-ss",str(start),"-i",SRC,
                    "-t",str(dur),
                    "-vf","scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,format=yuv420p",
                    "-r","24","-an","-c:v","libx264","-crf","20","-preset","medium",
                    tmp], check=True)
    # 2) burn the caption on (upper-left, same style as photo clips)
    cap_png = os.path.join(CLIPS, f"{name}_footage_cap.png")
    caption_overlay(cap).save(cap_png)
    out = os.path.join(CLIPS, name + ".mp4")
    subprocess.run(["ffmpeg","-y","-v","error","-i",tmp,"-i",cap_png,
                    "-filter_complex","[0:v][1:v]overlay=0:0",
                    "-c:v","libx264","-pix_fmt","yuv420p","-crf","20","-preset","medium",
                    "-movflags","+faststart", out], check=True)
    os.remove(tmp); os.remove(cap_png)
    print(f"{name}: footage {dur}s ({start}s in source) -> {out}", flush=True)
print("FOOTAGE CLIPS DONE")
