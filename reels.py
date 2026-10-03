import subprocess
import numpy as np
from PIL import Image, ImageFilter
from imageio_ffmpeg import get_ffmpeg_exe

W, H = 1080, 1920


def _frame_at(card, bg, t, kind, duration):
    if kind == "wide_in":
        k = 1.0 + 0.08 * (t / max(duration, 0.01))
        dx = 0
    elif kind == "detail":
        k = 1.35 + 0.05 * (t / max(duration, 0.01))
        dx = 0
    elif kind == "wide_out":
        k = 1.05
        dx = int(40 * np.sin(t * 1.2))
    else:
        k = 1.05
        dx = 0

    w, h = int(card.width * k), int(card.height * k)
    x = (W - w) // 2 + dx
    y = (H - h) // 2

    # Scale only the part of the card that is visible in the frame instead of the
    # whole enlarged card. The pixel grid is identical to resizing everything and
    # cropping afterwards, so the picture is the same but renders much faster.
    vx0, vy0 = max(x, 0), max(y, 0)
    vx1, vy1 = min(x + w, W), min(y + h, H)
    frame = bg.copy()
    if vx1 > vx0 and vy1 > vy0:
        box = (
            (vx0 - x) * card.width / w,
            (vy0 - y) * card.height / h,
            (vx1 - x) * card.width / w,
            (vy1 - y) * card.height / h,
        )
        part = card.resize((vx1 - vx0, vy1 - vy0), Image.Resampling.LANCZOS, box=box)
        frame.paste(part, (vx0, vy0))
    return np.asarray(frame, dtype=np.uint8)


def make_reel(card_path, out_path, duration=8, music_path=None, caption=None):
    card = Image.open(card_path).convert("RGB")

    s = max(W / card.width, H / card.height)
    bg = card.resize((int(card.width * s) + 1, int(card.height * s) + 1), Image.Resampling.LANCZOS)
    x, y = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((x, y, x + W, y + H)).filter(ImageFilter.GaussianBlur(45))

    fg = card.resize((W, max(1, int(card.height * W / card.width))), Image.Resampling.LANCZOS)

    scenes = [("wide_in", 0.35), ("detail", 0.35), ("wide_out", 0.30)]
    bounds = []
    acc = 0.0
    for name, frac in scenes:
        bounds.append((name, acc, acc + frac))
        acc += frac

    fps = 30
    total_frames = max(1, int(round(duration * fps)))
    ffmpeg = get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
    ]

    if music_path:
        cmd += ["-i", music_path, "-shortest", "-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "128k"]
    else:
        cmd += ["-an"]

    cmd += [
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", out_path,
    ]

    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for frame_index in range(total_frames):
            t = frame_index / fps
            scene_name = "wide_in"
            local_t = t
            local_dur = duration
            for name, t0, t1 in bounds:
                if t0 * duration <= t < t1 * duration:
                    scene_name = name
                    local_t = t - t0 * duration
                    local_dur = (t1 - t0) * duration
                    break
            frame = _frame_at(fg, bg, local_t, scene_name, max(local_dur, 0.01))
            process.stdin.write(frame)
        process.stdin.close()
        stderr = process.stderr.read().decode("utf-8", errors="replace")
        return_code = process.wait()
    except Exception:
        try:
            process.stdin.close()
        except Exception:
            pass
        process.kill()
        process.wait()
        raise

    if return_code != 0:
        raise RuntimeError(f"FFmpeg не смог создать Reels: {stderr[-1200:]}")

    return out_path
