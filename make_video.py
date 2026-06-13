from moviepy import ImageClip, CompositeVideoClip, concatenate_videoclips, ColorClip
from moviepy.video.fx import CrossFadeIn, CrossFadeOut
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import os

# Instagramリール/ストーリーズ 9:16
W, H = 1080, 1920
FONT_PATH = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
IMAGE_DIR = "/home/user/kanoyasika/images"
OUTPUT = "/home/user/kanoyasika/shikanoya_reel.mp4"

images = sorted([f for f in os.listdir(IMAGE_DIR) if f.endswith(".jpg")])

# テロップシーケンス (画像index, テキスト, サイズ)
captions = [
    "奈良公園のすぐそばに\n鹿がやってくる宿があります",
    "ここは「鹿のや」\n鹿と人が共に息づく場所",
    "窓の外に\n当たり前のように鹿がいる",
    "自然と溶け合う\nひとときを",
    "鹿のや\n奈良・自然との共存",
    "— 鹿のや —\nNARA / SHIKANOYA",
    "奈良の自然に\nただいまを言える宿",
]

def crop_and_resize(img_path, w, h):
    img = Image.open(img_path).convert("RGB")
    iw, ih = img.size
    # センタークロップ
    scale = max(w / iw, h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - w) // 2
    top = (nh - h) // 2
    img = img.crop((left, top, left + w, top + h))
    return img

def add_caption(img_pil, text, font_size=62):
    overlay = Image.new("RGBA", img_pil.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # グラデーション風の暗いオーバーレイ（下半分）
    gradient = Image.new("RGBA", img_pil.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(gradient)
    for y in range(img_pil.height):
        if y > img_pil.height * 0.5:
            alpha = int(180 * (y - img_pil.height * 0.5) / (img_pil.height * 0.5))
            gd.line([(0, y), (img_pil.width, y)], fill=(0, 0, 0, min(alpha, 170)))

    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
        font_small = ImageFont.truetype(FONT_PATH, 36)
    except:
        font = ImageFont.load_default()
        font_small = font

    lines = text.split("\n")
    line_heights = []
    line_widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    total_h = sum(line_heights) + (len(lines) - 1) * 20
    y_start = img_pil.height - total_h - 100

    result = img_pil.convert("RGBA")
    result = Image.alpha_composite(result, gradient)
    draw2 = ImageDraw.Draw(result)

    for i, line in enumerate(lines):
        x = (img_pil.width - line_widths[i]) // 2
        y = y_start + sum(line_heights[:i]) + i * 20
        # 影
        draw2.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 180))
        # 本文
        draw2.text((x, y), line, font=font, fill=(255, 255, 255, 240))

    return result.convert("RGB")

clips = []
n = len(images)
total_dur = 30.0
# 最後のシーンは少し長め
dur_per = [3.5, 3.5, 4.0, 4.5, 4.5, 5.0, 5.0]

for i, fname in enumerate(images):
    img_path = os.path.join(IMAGE_DIR, fname)
    cap_text = captions[i] if i < len(captions) else ""
    dur = dur_per[i] if i < len(dur_per) else 4.0

    pil_img = crop_and_resize(img_path, W, H)
    pil_with_cap = add_caption(pil_img, cap_text)

    arr = np.array(pil_with_cap)
    clip = ImageClip(arr, duration=dur)

    # ケンバーンズ風ズームイン
    scale_start = 1.0
    scale_end = 1.08
    def make_zoom(c, ss, se):
        def effect(get_frame, t):
            frame = get_frame(t)
            s = ss + (se - ss) * (t / c.duration)
            h, w = frame.shape[:2]
            nh, nw = int(h * s), int(w * s)
            pil = Image.fromarray(frame).resize((nw, nh), Image.LANCZOS)
            left = (nw - w) // 2
            top = (nh - h) // 2
            return np.array(pil.crop((left, top, left + w, top + h)))
        return effect
    clip = clip.transform(make_zoom(clip, scale_start, scale_end), apply_to="video")

    clips.append(clip)

# クロスフェードでつなぐ
fade = 0.5
final_clips = []
for i, c in enumerate(clips):
    if i == 0:
        final_clips.append(c.with_effects([CrossFadeOut(fade)]))
    elif i == len(clips) - 1:
        final_clips.append(c.with_effects([CrossFadeIn(fade)]))
    else:
        final_clips.append(c.with_effects([CrossFadeIn(fade), CrossFadeOut(fade)]))

video = concatenate_videoclips(final_clips, method="compose", padding=-fade)
video = video.with_fps(30)

video.write_videofile(
    OUTPUT,
    fps=30,
    codec="libx264",
    audio=False,
    preset="medium",
    ffmpeg_params=["-crf", "20", "-pix_fmt", "yuv420p"],
    logger="bar",
)
print(f"\n完成: {OUTPUT}")
