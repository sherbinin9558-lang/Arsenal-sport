import numpy as np

from PIL import Image, ImageFilter

from moviepy.editor import VideoClip, AudioFileClip



W, H = 1080, 1920





def make_reel(card_path, out_path, duration=8, music_path=None, zoom=0.07):

    card = Image.open(card_path).convert("RGB")



    s = max(W / card.width, H / card.height)

    bg = card.resize((int(card.width * s) + 1, int(card.height * s) + 1), Image.LANCZOS)

    x, y = (bg.width - W) // 2, (bg.height - H) // 2

    bg = bg.crop((x, y, x + W, y + H)).filter(ImageFilter.GaussianBlur(45))



    fg = card.resize((W, int(card.height * W / card.width)), Image.LANCZOS)



    def make_frame(t):

        k = 1 + zoom * (t / duration)

        w, h = int(fg.width * k), int(fg.height * k)

        img = fg.resize((w, h), Image.LANCZOS)

        frame = bg.copy()

        frame.paste(img, ((W - w) // 2, (H - h) // 2))

        return np.array(frame)



    clip = VideoClip(make_frame, duration=duration).fadein(0.4).fadeout(0.4)



    if music_path:

        audio = AudioFileClip(music_path).subclip(0, duration).audio_fadeout(1)

        clip = clip.set_audio(audio)



    clip.write_videofile(

        out_path, fps=30, codec="libx264", audio_codec="aac",

        preset="veryfast", logger=None,

    )

    return out_path
