from moviepy import ImageClip, VideoClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
from moviepy.video.fx import CrossFadeIn, CrossFadeOut
from moviepy.audio.fx import AudioFadeOut
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os

# Instagramリール/ストーリーズ 9:16
W, H = 1080, 1920
FONT_PATH = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
IMAGE_DIR = "/home/user/kanoyasika/images"
MUSIC = "/root/.claude/uploads/33d0e5f7-0f54-5025-8014-9de9b9ef7d8c/c39454ae-Soft_Path_through_the_Cedar.mp3"
OUTPUT = "/home/user/kanoyasika/shikanoya_reel.mp4"

images = sorted([f for f in os.listdir(IMAGE_DIR) if f.endswith(".jpg")])

# 最後の画像をテロップなしで追加（8シーン目）
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

# 最後の画像を繰り返す（8シーン目）
images_seq = images + [images[-1]]
dur_per = [3.5, 3.5, 4.0, 4.5, 4.5, 5.0, 4.0, 4.0]

def crop_and_resize(img_path, w, h):
    img = Image.open(img_path).convert("RGB")
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - w) // 2
    top = (nh - h) // 2
    return img.crop((left, top, left + w, top + h))

def make_caption_frame(text, w, h, font_size=68):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if not text:
        return np.array(img)

    for y in range(h):
        if y > h * 0.55:
            alpha = int(185 * (y - h * 0.55) / (h * 0.45))
            draw.line([(0, y), (w, y)], fill=(0, 0, 0, min(alpha, 175)))

    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except:
        font = ImageFont.load_default()

    lines = text.split("\n")
    line_heights, line_widths = [], []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    total_h = sum(line_heights) + (len(lines) - 1) * 24
    y_start = h - total_h - 130

    for i, line in enumerate(lines):
        x = (w - line_widths[i]) // 2
        y = y_start + sum(line_heights[:i]) + i * 24
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 180))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 245))

    return np.array(img)

def make_zoom_clip(bg_arr, dur, scale_start=1.0, scale_end=1.08):
    h, w = bg_arr.shape[:2]
    def zoom_frame(t):
        s = scale_start + (scale_end - scale_start) * (t / dur)
        nh, nw = int(h * s), int(w * s)
        pil = Image.fromarray(bg_arr).resize((nw, nh), Image.LANCZOS)
        left = (nw - w) // 2
        top = (nh - h) // 2
        return np.array(pil.crop((left, top, left + w, top + h)))
    return VideoClip(zoom_frame, duration=dur)

clips = []
for i, fname in enumerate(images_seq):
    img_path = os.path.join(IMAGE_DIR, fname)
    cap_text = captions[i] if i < len(captions) else ""
    dur = dur_per[i] if i < len(dur_per) else 4.0

    bg = np.array(crop_and_resize(img_path, W, H))
    bg_clip = make_zoom_clip(bg, dur)

    cap_arr = make_caption_frame(cap_text, W, H)
    cap_clip = ImageClip(cap_arr, duration=dur)

    scene = CompositeVideoClip([bg_clip, cap_clip], size=(W, H))
    clips.append(scene)

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

# 音楽を動画の長さに合わせてフェードアウト
audio = AudioFileClip(MUSIC)
video_dur = video.duration
if audio.duration > video_dur:
    audio = audio.subclipped(0, video_dur).with_effects([AudioFadeOut(2.0)])
video = video.with_audio(audio)

print(f"動画尺: {video_dur:.2f}秒")
video.write_videofile(
    OUTPUT,
    fps=30,
    codec="libx264",
    audio_codec="aac",
    preset="medium",
    ffmpeg_params=["-crf", "20", "-pix_fmt", "yuv420p"],
    logger="bar",
)
print(f"\n完成: {OUTPUT}")
