import unittest

try:
    import numpy as np
    from PIL import Image
    import reels
    HAS_DEPS = True
except Exception:  # CI without optional packages
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "numpy, Pillow and imageio-ffmpeg are required")
class ReelsFrameTests(unittest.TestCase):
    """The optimised frame renderer must match the plain resize-then-paste result."""

    @staticmethod
    def _reference(card, bg, t, kind, duration):
        if kind == "wide_in":
            k, dx = 1.0 + 0.08 * (t / max(duration, 0.01)), 0
        elif kind == "detail":
            k, dx = 1.35 + 0.05 * (t / max(duration, 0.01)), 0
        else:
            k, dx = 1.05, int(40 * np.sin(t * 1.2))
        w, h = int(card.width * k), int(card.height * k)
        frame = bg.copy()
        frame.paste(card.resize((w, h), Image.Resampling.LANCZOS), ((reels.W - w) // 2 + dx, (reels.H - h) // 2))
        return np.asarray(frame, dtype=np.uint8)

    def test_frames_match_reference(self):
        card = Image.effect_noise((reels.W, 1350), 60).convert("RGB")
        bg = Image.new("RGB", (reels.W, reels.H), (20, 20, 40))
        for kind in ("wide_in", "detail", "wide_out"):
            for t in (0.0, 0.7, 1.4):
                got = reels._frame_at(card, bg, t, kind, 2.8)
                want = self._reference(card, bg, t, kind, 2.8)
                self.assertEqual(got.shape, (reels.H, reels.W, 3))
                self.assertLessEqual(int(np.abs(got.astype(int) - want.astype(int)).max()), 3, (kind, t))


if __name__ == "__main__":
    unittest.main()
