import io
import unittest

from PIL import Image, ImageDraw

from image_utils import open_photo


def _phone_photo(orientation):
    """A 1600x1200 JPEG with a red block top-left, tagged like a phone would."""
    img = Image.new("RGB", (1600, 1200), (30, 60, 110))
    ImageDraw.Draw(img).rectangle((0, 0, 300, 300), fill=(255, 0, 0))
    exif = Image.Exif()
    exif[0x0112] = orientation
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    return io.BytesIO(buf.getvalue())


class OpenPhotoTests(unittest.TestCase):
    def test_portrait_phone_photo_is_rotated_upright(self):
        self.assertEqual(open_photo(_phone_photo(6)).size, (1200, 1600))
        self.assertEqual(open_photo(_phone_photo(8)).size, (1200, 1600))

    def test_photo_without_orientation_is_unchanged(self):
        buf = io.BytesIO()
        Image.new("RGB", (800, 600), (1, 2, 3)).save(buf, "JPEG")
        buf.seek(0)
        self.assertEqual(open_photo(buf).size, (800, 600))

    def test_requested_mode_is_applied(self):
        buf = io.BytesIO()
        Image.new("RGBA", (10, 10), (1, 2, 3, 4)).save(buf, "PNG")
        buf.seek(0)
        self.assertEqual(open_photo(buf, "RGBA").mode, "RGBA")
        buf.seek(0)
        self.assertEqual(open_photo(buf).mode, "RGB")


class SourceHandlingTests(unittest.TestCase):
    def test_max_bulk_upload_stores_base64_not_a_file_path(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / "ui" / "max.py").read_text(encoding="utf-8")
        self.assertNotIn('products_now[idx]["original_image"] = path', source)
        self.assertIn('products_now[idx]["original_image"] = base64.b64encode(', source)


if __name__ == "__main__":
    unittest.main()
