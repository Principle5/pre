"""Render v2 motion clips for the United Front video.
Upgrades over v1: varied camera moves (push-in / push-out / pan / diagonal),
on-screen photo captions, gentle vignette + subtle film grain on the
historical photos. Output: 1280x720, 24fps, libx264 MP4s.
"""
import os, subprocess, sys, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = os.path.expanduser("~/workspace/video-united-front")
CLIPS = os.path.join(BASE, "clips2")
os.makedirs(CLIPS, exist_ok=True)

W, H = 1280, 720
FPS = 24
SERIF_B = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
SANS_B = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

def smoothstep(t):
    return 3*t*t - 2*t*t*t

def font(path, size):
    # Noto CJK .ttc order: 0=JP, 1=KR, 2=SC, 3=TC, 4=HK.
    # PIL defaults to index 0 (JP). We must use index 2 (SC) so Chinese
    # glyphs (e.g. 关) render in their Simplified-Chinese form, not the
    # Japanese variant. This was the root cause of the recurring 关 issue.
    return ImageFont.truetype(path, size, index=2)

# --- vignette mask (darken corners ~18%) ---
_vig = Image.new("L", (W, H), 0)
_dv = ImageDraw.Draw(_vig)
_dv.ellipse((-W*0.25, -H*0.45, W*1.25, H*1.45), fill=255)
_vig = _vig.filter(ImageFilter.GaussianBlur(180))
_vig_np = np.asarray(_vig, dtype=np.float32) / 255.0
_vig_factor = 1.0 - 0.18 * (1.0 - _vig_np)   # 1.0 centre -> 0.82 corners

# --- film grain: 6 pre-generated noise patterns, cycled ---
_rng = np.random.default_rng(7)
_grain = [(_rng.normal(0, 6.0, (H, W, 1))).astype(np.float32) for _ in range(6)]

SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"

def caption_overlay(text):
    """Photo caption, upper-left, Song-style serif (Noto Serif CJK SC,
    the closest installed equivalent to 华文中宋). Returns RGBA (W,H)."""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    f = font(SERIF, 36)
    bbox = d.textbbox((0, 0), text, font=f)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    x, y = 36, 36
    d.rounded_rectangle([x-16, y-12, x+tw+18, y+th+16], radius=8,
                        fill=(0, 0, 0, 110))
    d.text((x, y), text, font=f, fill=(245, 240, 228, 255))
    return ov

def section_title_overlay(text):
    """Large centred section title (gold serif) with a soft dark band.
    Returns RGBA (W,H); caller fades it in/out by scaling its alpha."""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    f = font(SERIF_B, 72)
    bbox = d.textbbox((0, 0), text, font=f)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    x, y = (W-tw)//2, H//2 - th//2 - 20
    # soft dark band behind the title for legibility
    d.rectangle([0, y-28, W, y+th+28], fill=(0, 0, 0, 90))
    d.text((x, y), text, font=f, fill=(201, 164, 74, 255))
    return ov

def render_motion(name, src, dur, motion, caption=None, historical=True,
                  section_title=None):
    im = Image.open(src).convert("RGB")
    iw, ih = im.size
    # Portrait photos (e.g. 台儿庄 590x636) must NOT be cover-cropped into
    # 16:9 — that cuts away ~54% of the height (heads and legs gone, only
    # torsos left). Instead: blurred darkened background fill + the full
    # photo fitted in the frame, with a gentle zoom on the foreground.
    portrait = iw < ih
    if portrait:
        # background: cover, heavily blurred + darkened
        s_bg = max(W/iw, H/ih)
        bg = im.resize((round(iw*s_bg), round(ih*s_bg)), Image.LANCZOS)
        # centre-crop bg to frame
        bx = (bg.width - W)//2; by = (bg.height - H)//2
        bg = bg.crop((bx, by, bx+W, by+H))
        bg = bg.filter(ImageFilter.GaussianBlur(28))
        bg = Image.fromarray(np.clip(np.asarray(bg, dtype=np.float32)*0.45, 0, 255).astype(np.uint8))
        # foreground: fit inside frame (full photo visible)
        s_fg = min(W*0.92/iw, H*0.92/ih)
        fg_w, fg_h = round(iw*s_fg), round(ih*s_fg)
        fg = im.resize((fg_w, fg_h), Image.LANCZOS)
        n = max(1, round(dur*FPS))
        cap = caption_overlay(caption) if caption else None
        st = section_title_overlay(section_title) if section_title else None
        out = os.path.join(CLIPS, name + ".mp4")
        cmd = ["ffmpeg","-y","-v","error",
               "-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
               "-c:v","libx264","-pix_fmt","yuv420p","-crf","20","-preset","medium",
               "-movflags","+faststart", out]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for i in range(n):
            t = i/(n-1) if n > 1 else 0
            e = smoothstep(t)
            # gentle shrink: foreground 1.06 -> 1.00 (clearly gets smaller)
            z = 1.06 - 0.06*e
            zw, zh = round(fg_w*z), round(fg_h*z)
            fr_fg = fg.resize((zw, zh), Image.LANCZOS)
            fr = bg.copy()
            fr.paste(fr_fg, ((W-zw)//2, (H-zh)//2))
            if historical:
                arr = np.asarray(fr, dtype=np.float32)
                arr *= _vig_factor[..., None]
                arr += _grain[i % len(_grain)]
                fr = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
            if cap is not None or st is not None:
                fr = fr.convert("RGBA")
                if cap is not None:
                    fr.paste(cap, (0, 0), cap)
                if st is not None:
                    tsec = i / FPS
                    if tsec < 0.8:
                        a = tsec / 0.8
                    elif tsec < 2.8:
                        a = 1.0
                    elif tsec < 3.6:
                        a = 1.0 - (tsec - 2.8) / 0.8
                    else:
                        a = 0.0
                    if a > 0:
                        r, g, b, al = st.split()
                        al = al.point(lambda v: int(v * a))
                        st_a = Image.merge("RGBA", (r, g, b, al))
                        fr.paste(st_a, (0, 0), st_a)
                fr = fr.convert("RGB")
            p.stdin.write(fr.tobytes())
        p.stdin.close(); p.wait()
        if p.returncode != 0:
            raise RuntimeError(f"ffmpeg failed for {name}")
        print(f"{name}: {dur}s portrait-fit -> {out}", flush=True)
        return
    # base scaled to cover frame*1.14 (headroom; v7 zoom 1.00<->1.09 is the
    # middle ground — v5's 1.12 cropped too tight, v6's 1.06 felt static)
    s = max(W*1.14/iw, H*1.14/ih)
    base = im.resize((round(iw*s), round(ih*s)), Image.LANCZOS)
    bw, bh = base.size
    cx0, cy0 = bw/2, bh/2
    n = max(1, round(dur*FPS))
    cap = caption_overlay(caption) if caption else None
    st = section_title_overlay(section_title) if section_title else None
    out = os.path.join(CLIPS, name + ".mp4")
    cmd = ["ffmpeg","-y","-v","error",
           "-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
           "-c:v","libx264","-pix_fmt","yuv420p","-crf","20","-preset","medium",
           "-movflags","+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        t = i/(n-1) if n > 1 else 0
        e = smoothstep(t)
        # motion -> (zoom, centre dx, centre dy) as fractions of frame
        # middle range (v7): zoom 1.00<->1.09, pan +/-0.06 — visible motion,
        # photos stay readable (v5 1.12 too tight, v6 1.06 too static)
        if motion == "in":
            z = 1.00 + 0.09*e; dx, dy = 0.0, 0.0
        elif motion == "out":
            z = 1.09 - 0.09*e; dx, dy = 0.0, 0.0
        elif motion == "pan_l":   # view drifts left
            z = 1.06; dx = 0.06 - 0.12*e; dy = 0.0
        elif motion == "pan_r":   # view drifts right
            z = 1.06; dx = -0.06 + 0.12*e; dy = 0.0
        elif motion == "diag":    # zoom in + drift up-right
            z = 1.00 + 0.09*e; dx = -0.045 + 0.09*e; dy = 0.03 - 0.06*e
        else:
            z = 1.00 + 0.09*e; dx, dy = 0.0, 0.0
        cw, ch = W/z, H/z
        cx = cx0 + dx*W
        cy = cy0 + dy*H
        box = (cx-cw/2, cy-ch/2, cx+cw/2, cy+ch/2)
        fr = base.resize((W, H), Image.LANCZOS, box=box)
        if historical:
            arr = np.asarray(fr, dtype=np.float32)
            arr *= _vig_factor[..., None]
            arr += _grain[i % len(_grain)]
            fr = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        if cap is not None or st is not None:
            fr = fr.convert("RGBA")
            if cap is not None:
                fr.paste(cap, (0, 0), cap)
            if st is not None:
                # section title: fade in 0.8s, hold to 2.8s, fade out by 3.6s
                tsec = i / FPS
                if tsec < 0.8:
                    a = tsec / 0.8
                elif tsec < 2.8:
                    a = 1.0
                elif tsec < 3.6:
                    a = 1.0 - (tsec - 2.8) / 0.8
                else:
                    a = 0.0
                if a > 0:
                    r, g, b, al = st.split()
                    al = al.point(lambda v: int(v * a))
                    st_a = Image.merge("RGBA", (r, g, b, al))
                    fr.paste(st_a, (0, 0), st_a)
            fr = fr.convert("RGB")
        p.stdin.write(fr.tobytes())
    p.stdin.close(); p.wait()
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {name}")
    print(f"{name}: {dur}s {motion} -> {out}", flush=True)

def title_card(name, title, subtitle, sub2=None, dur=8):
    img = Image.new("RGB", (W, H), (10, 9, 8))
    d = ImageDraw.Draw(img)
    f_title = font(SERIF_B, 92)
    # Subtitle in Regular (not Bold): at 40px the Bold 关 looked heavy and
    # muddy on video; Regular renders 关 cleaner and gives a better
    # title/subtitle hierarchy.
    f_sub = font(SERIF, 40)
    f_sub2 = font(SERIF, 30)
    bbox = d.textbbox((0, 0), title, font=f_title)
    tw = bbox[2]-bbox[0]
    y = H//2 - 120
    d.text(((W-tw)/2, y), title, font=f_title, fill=(201, 164, 74))
    # gold rule spans the full width of the title text (both ends)
    d.line([((W-tw)/2, y+125), ((W+tw)/2, y+125)], fill=(201, 164, 74), width=3)
    bbox = d.textbbox((0, 0), subtitle, font=f_sub)
    sw = bbox[2]-bbox[0]
    d.text(((W-sw)/2, y+185), subtitle, font=f_sub, fill=(232, 222, 205))
    if sub2:
        bbox = d.textbbox((0, 0), sub2, font=f_sub2)
        sw = bbox[2]-bbox[0]
        d.text(((W-sw)/2, y+245), sub2, font=f_sub2, fill=(170, 160, 145))
    png = os.path.join(CLIPS, name + ".png")
    img.save(png)
    out = os.path.join(CLIPS, name + ".mp4")
    subprocess.run(["ffmpeg","-y","-v","error","-loop","1","-i",png,
                    "-t",str(dur),"-c:v","libx264","-pix_fmt","yuv420p",
                    "-r",str(FPS),"-movflags","+faststart", out], check=True)
    print(f"{name}: title card {dur}s -> {out}", flush=True)

KP = os.path.expanduser("~/workspace/kangzhan-ppt")
IMG = os.path.join(BASE, "images")

# (name, source, duration, motion, caption, historical, section_title)
JOBS = [
    ("A1", os.path.join(BASE, "images/lugou/Army_29_Fighting_1937.jpg"), 17.9, "in", "卢沟桥 · 1937年7月", True, "走向联合"),
    ("A2", os.path.expanduser("~/workspace/kangzhan-ppt-package/ppt/assets/dec9_students.jpg"), 17.9, "pan_r", "一二·九运动 · 1935年12月", True, None),
    ("A3", os.path.join(KP, "united_front_more/eighth_route_marching.jpg"), 17.7, "pan_l", "八路军行军 · 1937年秋", True, None),
    ("B1", os.path.join(KP, "photos/pingxingguan.jpg"), 19.3, "out", "平型关 · 1937年9月", True, "两个战场"),
    ("B2", os.path.join(KP, "photos/taierzhuang.jpg"), 12.0, "out", "台儿庄 · 1938年", True, None),
    ("B3", os.path.join(KP, "united_front_more/sihang_warehouse.jpg"), 26.6, "out", "四行仓库 · 1937年", True, None),
    ("C1", os.path.join(KP, "united_front/huimin.jpg"), 15.5, "pan_r", "回民支队 · 1939—1940年", True, "各界同心"),
    ("C2", os.path.join(KP, "restored/burma_road_color.webp"), 15.5, "in", "滇缅公路 · 1937年", True, None),
    ("C3", os.path.join(KP, "united_front/convoy.jpg"), 15.5, "pan_l", "南侨机工 · 滇缅公路", True, None),
    ("C4", os.path.join(KP, "united_front/tan_kah_kee_1946.png"), 15.5, "out", "陈嘉庚 · 1946年", True, None),
    ("C5", os.path.join(KP, "united_front/sewing.jpg"), 15.3, "in", "上海缝衣妇女 · 1937年", True, None),
    ("D1", os.path.join(KP, "photos/bloody_saturday.jpg"), 13.1, "in", "上海南站 · 1937年8月28日", True, "后方"),
    ("D2", os.path.join(KP, "united_front_more/nanniwan.jpg"), 13.1, "pan_r", "南泥湾 · 1943年", True, None),
    ("D3", os.path.join(KP, "photos/nurse.jpg"), 13.1, "out", "战地护士 · 1944年", True, None),
    ("D4", os.path.join(KP, "united_front_more/students_corps.jpg"), 13.1, "pan_l", "学生军 · 1941—1942年", True, None),
    ("E1", os.path.join(IMG, "guangzhou/scut_south.jpg"), 15.7, "pan_r", "今天 · 校园", False, "今天"),
    ("E2", os.path.join(IMG, "guangzhou/canton_tower.jpg"), 15.7, "in", "今天 · 城市", False, None),
    ("E3", os.path.join(IMG, "guangzhou/zhujiang_night.jpg"), 15.6, "pan_l", "今天 · 珠江新城", False, None),
]

def resolve_modern():
    # v7: E1/E2/E3 now use real Guangzhou photos (Wikimedia Commons, CC BY-SA),
    # not the AI-generated webp files. The AI files remain in images/ unused.
    pass

if __name__ == "__main__":
    only = sys.argv[1:] or None
    resolve_modern()
    for name, src, dur, motion, cap, hist, st in JOBS:
        if only and name not in only:
            continue
        if src is None or not os.path.exists(src):
            print(f"SKIP {name}: missing {src}", flush=True); continue
        render_motion(name, src, dur, motion, cap, hist, section_title=st)
    if not only or "title_open" in only:
        title_card("title_open", "抗日民族统一战线", "一段关于团结的历史", "1937 — 1945", dur=10)
    if not only or "title_close" in only:
        title_card("title_close", "记住历史，珍爱和平", "一个国家最强大的时候，是所有人站在一起的时候", "背景音乐：Echoes in the Archive — Sascha Ende（CC BY 4.0）", dur=16)
    print("RENDER V2 DONE", flush=True)
