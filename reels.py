
import numpy as np

from PIL import Image, ImageFilter

from moviepy.editor import VideoClip, AudioFileClip



W, H = 1080, 1920





def _frame_at(card, bg, t, kind, duration):

    """kind: 'wide_in' (наезд с общего), 'detail' (приближение к центру верх),

    'wide_out' (общий план со сдвигом в сторону), 'end' (статичный финал)."""

    if kind == "wide_in":

        k = 1.0 + 0.08 * (t / duration)

        dx = 0

    elif kind == "detail":

        k = 1.35 + 0.05 * (t / duration)

        dx = 0

    elif kind == "wide_out":

        k = 1.05

        dx = int(40 * np.sin(t * 1.2))

    else:  # end

        k = 1.05

        dx = 0



    w, h = int(card.width * k), int(card.height * k)

    img = card.resize((w, h), Image.LANCZOS)

    frame = bg.copy()

    x = (W - w) // 2 + dx

    y = (H - h) // 2

    frame.paste(img, (x, y))

    return np.array(frame)





def make_reel(card_path, out_path, duration=8, music_path=None, caption=None):

    card = Image.open(card_path).convert("RGB")



    s = max(W / card.width, H / card.height)

    bg = card.resize((int(card.width * s) + 1, int(card.height * s) + 1), Image.LANCZOS)

    x, y = (bg.width - W) // 2, (bg.height - H) // 2

    bg = bg.crop((x, y, x + W, y + H)).filter(ImageFilter.GaussianBlur(45))



    fg = card.resize((W, int(card.height * W / card.width)), Image.LANCZOS)



    # Таймлайн сцен: доля от общей длительности

    scenes = [

        ("wide_in", 0.35),

        ("detail", 0.35),

        ("wide_out", 0.30),

    ]

    bounds = []

    acc = 0.0

    for name, frac in scenes:

        bounds.append((name, acc, acc + frac))

        acc += frac



    def make_frame(t):

        for name, t0, t1 in bounds:

            if t0 * duration <= t < t1 * duration or (name == bounds[-1][0] and t >= t1 * duration):

                local_t = t - t0 * duration

                local_dur = (t1 - t0) * duration

                return _frame_at(fg, bg, local_t, name, max(local_dur, 0.01))

        return _frame_at(fg, bg, 0, "wide_in", duration)



    clip = VideoClip(make_frame, duration=duration).fadein(0.3).fadeout(0.3)



    if music_path:

        audio = AudioFileClip(music_path).subclip(0, duration).audio_fadeout(1)

        clip = clip.set_audio(audio)



    clip.write_videofile(

        out_path, fps=30, codec="libx264", audio_codec="aac",

        preset="veryfast", logger=None,

    )

    return out_path
