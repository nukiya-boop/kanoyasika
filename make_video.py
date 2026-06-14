import subprocess, os, shutil, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FFMPEG = "/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
W, H = 1080, 1920
FPS = 30
FONT_PATH = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
IMAGE_DIR = "/home/user/kanoyasika/images"
MUSIC = "/root/.claude/uploads/33d0e5f7-0f54-5025-8014-9de9b9ef7d8c/c39454ae-Soft_Path_through_the_Cedar.mp3"
OUTPUT = "/home/user/kanoyasika/shikanoya_reel.mp4"

images_seq = sorted([f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(".jpg") or f.lower().endswith(".jpeg")])
# 最後に7C1A4282.JPGをテロップなしで追加
images_seq = [f for f in images_seq if f != "7C1A4282.JPG"] + ["7C1A4282.JPG"]

captions = [
    "奈良公園のすぐそばに\n鹿がやってくる宿",
    "ここは「鹿のや」\n鹿と人が共に息づく場所",
    "窓の外に\n当たり前のように鹿がいる",
    "自然と溶け合う\nひとときを",
    "鹿のや\n奈良・自然との共存",
    "— 鹿のや —\nNARA KANOYA",
    "奈良の自然に\nただいまを言える宿",
    "",  # 最後：テロップなし
]
dur_per = [3.5, 3.5, 4.0, 4.5, 4.5, 5.0, 4.0, 4.0]
FADE = 0.5  # クロスフェード秒数

def crop_resize(path, w, h):
    img = Image.open(path).convert("RGB")
    iw, ih = img.size
    s = max(w/iw, h/ih)
    nw, nh = int(iw*s), int(ih*s)
    img = img.resize((nw, nh), Image.LANCZOS)
    return img.crop(((nw-w)//2, (nh-h)//2, (nw-w)//2+w, (nh-h)//2+h))

def add_caption(base_pil, text, font_size=68):
    out = base_pil.convert("RGBA")
    overlay = Image.new("RGBA", out.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    if text:
        for y in range(H):
            if y > H*0.55:
                a = int(175*(y-H*0.55)/(H*0.45))
                draw.line([(0,y),(W,y)], fill=(0,0,0,min(a,170)))
        try:
            font = ImageFont.truetype(FONT_PATH, font_size)
        except:
            font = ImageFont.load_default()
        lines = text.split("\n")
        lh, lw = [], []
        td = ImageDraw.Draw(Image.new("RGBA",(1,1)))
        for ln in lines:
            bb = td.textbbox((0,0), ln, font=font)
            lw.append(bb[2]-bb[0]); lh.append(bb[3]-bb[1])
        th = sum(lh)+(len(lines)-1)*24
        y0 = H-th-130
        for i,ln in enumerate(lines):
            x = (W-lw[i])//2
            y = y0+sum(lh[:i])+i*24
            draw.text((x+2,y+2), ln, font=font, fill=(0,0,0,190))
            draw.text((x,y), ln, font=font, fill=(255,255,255,245))
    out = Image.alpha_composite(out, overlay)
    return out.convert("RGB")

def zoom_frame(pil, t, dur, s0=1.0, s1=1.08):
    s = s0 + (s1-s0)*(t/dur)
    nw, nh = int(W*s), int(H*s)
    img = pil.resize((nw,nh), Image.LANCZOS)
    return img.crop(((nw-W)//2,(nh-H)//2,(nw-W)//2+W,(nh-H)//2+H))

# フレームをtmpフォルダに書き出す
tmpdir = tempfile.mkdtemp()
frame_idx = 0

for scene_i, fname in enumerate(images_seq):
    path = os.path.join(IMAGE_DIR, fname)
    cap = captions[scene_i] if scene_i < len(captions) else ""
    dur = dur_per[scene_i] if scene_i < len(dur_per) else 4.0
    nframes = int(dur * FPS)
    fade_in_frames  = int(FADE * FPS) if scene_i > 0 else 0
    fade_out_frames = int(FADE * FPS) if scene_i < len(images_seq)-1 else 0

    base = crop_resize(path, W, H)

    for f in range(nframes):
        t = f / FPS
        zoomed = zoom_frame(base, t, dur)
        frame = add_caption(zoomed, cap)
        arr = np.array(frame, dtype=np.uint8)

        # フェードイン
        if f < fade_in_frames:
            alpha = f / fade_in_frames
            arr = (arr * alpha).astype(np.uint8)
        # フェードアウト
        if f >= nframes - fade_out_frames:
            alpha = (nframes - f) / fade_out_frames
            arr = (arr * alpha).astype(np.uint8)

        img_out = Image.fromarray(arr)
        img_out.save(os.path.join(tmpdir, f"frame_{frame_idx:06d}.jpg"), quality=92)
        frame_idx += 1

total_frames = frame_idx
print(f"フレーム書き出し完了: {total_frames}フレーム ({total_frames/FPS:.1f}秒)")

# ffmpegで動画+音楽を合成
cmd = [
    FFMPEG, "-y",
    "-framerate", str(FPS),
    "-i", os.path.join(tmpdir, "frame_%06d.jpg"),
    "-i", MUSIC,
    "-c:v", "libx264",
    "-profile:v", "high",
    "-level:v", "4.0",
    "-pix_fmt", "yuv420p",
    "-crf", "20",
    "-preset", "medium",
    "-c:a", "aac",
    "-b:a", "192k",
    "-shortest",
    "-movflags", "+faststart",
    OUTPUT
]
print("ffmpegでエンコード中...")
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print("STDERR:", result.stderr[-2000:])
else:
    print(f"\n完成: {OUTPUT}")
    import os as _os
    print(f"サイズ: {_os.path.getsize(OUTPUT)//1024//1024}MB")

shutil.rmtree(tmpdir)
