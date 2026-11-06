import os, subprocess
from PIL import Image
import numpy as np

BASE = os.path.expanduser("~/workspace/kangzhan-ppt/restored")
TMP = os.path.join(BASE, "frames_tmp")
os.makedirs(TMP, exist_ok=True)

# (stem, source, mp4_out_name, gif_out_name)
JOBS = [
  ("pingxingguan", os.path.join(BASE,"pingxingguan_color.webp"), "pingxingguan_restore.mp4", "pingxingguan_restore.gif"),
  ("burma_road", os.path.join(BASE,"burma_road_color.webp"), "burma_road_restore.mp4", "burma_road_restore.gif"),
  ("expedition", os.path.join(BASE,"expedition_color.webp"), "expedition_restore.mp4", "expedition_restore.gif"),
  ("nurse", os.path.expanduser("~/workspace/kangzhan-ppt/photos/web/nurse.jpg"), "nurse_bw_motion.mp4", "nurse_bw_motion.gif"),
]

def smoothstep(t): return 3*t*t - 2*t*t*t

for stem, src, mp4name, gifname in JOBS:
    im = Image.open(src).convert("RGB")
    W,H = im.size
    ow, oh = 720, round(720*H/W)
    if oh % 2: oh += 1
    gw, gh = 640, round(640*H/W)
    if gh % 2: gh += 1
    d = os.path.join(TMP, stem); os.makedirs(d, exist_ok=True)
    N=144
    prev=None; diffs=[]
    for i in range(N):
        t = i/(N-1)
        z = 1 + 0.07*smoothstep(t)
        cw, ch = W/z, H/z
        box = (W/2-cw/2, H/2-ch/2, W/2+cw/2, H/2+ch/2)
        fr = im.resize((ow, oh), Image.LANCZOS, box=box)
        fr.save(os.path.join(d, f"f{i:03d}.png"))
        a = np.asarray(fr.convert("L"), dtype=np.float32)
        if prev is not None: diffs.append(float(np.mean(np.abs(a-prev))))
        prev=a
    print(stem, "frames", N, "mean|d|", round(sum(diffs)/len(diffs),3), "max|d|", round(max(diffs),3), flush=True)
    subprocess.run(["ffmpeg","-y","-v","error","-framerate","24","-i",os.path.join(d,"f%03d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-crf","20","-preset","medium","-movflags","+faststart", os.path.join(BASE,"mp4",mp4name)], check=True)
    gd = os.path.join(d,"gif"); os.makedirs(gd, exist_ok=True)
    for j,i in enumerate(range(0,N,2)):
        f2 = Image.open(os.path.join(d,f"f{i:03d}.png")).resize((gw, gh), Image.LANCZOS)
        f2.save(os.path.join(gd, f"g{j:03d}.png"))
    subprocess.run(["ffmpeg","-y","-v","error","-framerate","12","-i",os.path.join(gd,"g%03d.png"),"-vf","palettegen=max_colors=256:stats_mode=full", os.path.join(d,"pal.png")], check=True)
    subprocess.run(["ffmpeg","-y","-v","error","-framerate","12","-i",os.path.join(gd,"g%03d.png"),"-i",os.path.join(d,"pal.png"),"-lavfi","paletteuse=dither=bayer:bayer_scale=4", os.path.join(BASE,"gifs",gifname)], check=True)
    print(stem, "mp4+gif done", flush=True)
print("ALL DONE")
