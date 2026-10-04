"""Small helpers for user-supplied photos."""
from PIL import Image, ImageOps


def open_photo(source, mode="RGB"):
    """Open an uploaded photo and apply its EXIF orientation.

    Phones store portrait shots as sideways pixels plus an orientation tag;
    Pillow ignores that tag unless it is applied explicitly.
    """
    image = Image.open(source)
    try:
        image = ImageOps.exif_transpose(image)
    except Exception:
        pass
    return image.convert(mode)
