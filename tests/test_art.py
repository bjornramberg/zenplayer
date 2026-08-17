import numpy as np
from PIL import Image

from zenplayer.widgets._art import (
    _hex,
    crop_square,
    fallback_image,
    image_to_rows,
    pixels_to_rows,
    quantize_image,
)


def test_hex_black():
    assert _hex((0, 0, 0)) == "#000000"


def test_hex_white():
    assert _hex((255, 255, 255)) == "#ffffff"


def test_hex_known_color():
    assert _hex((255, 107, 107)) == "#ff6b6b"


def test_fallback_image_returns_pil_image():
    img = fallback_image(100, 50, "test_seed")
    assert isinstance(img, Image.Image)


def test_fallback_image_dimensions():
    img = fallback_image(80, 40, "test")
    assert img.size == (80, 40)


def test_fallback_image_deterministic_same_seed():
    img1 = fallback_image(50, 25, "seed1")
    img2 = fallback_image(50, 25, "seed1")
    assert list(img1.getdata()) == list(img2.getdata())


def test_fallback_image_different_seeds_different_palettes():
    img1 = fallback_image(50, 25, "seed_a")
    img2 = fallback_image(50, 25, "seed_b")
    assert list(img1.getdata()) != list(img2.getdata())


def test_fallback_image_zero_width():
    img = fallback_image(0, 25, "test")
    assert img.size[1] == 25


def test_fallback_image_zero_height():
    img = fallback_image(50, 0, "test")
    assert img.size[0] == 50


def test_crop_square_already_square():
    img = Image.new("RGB", (50, 50), (100, 100, 100))
    result = crop_square(img)
    assert result.size == (50, 50)


def test_crop_square_wider_than_tall():
    img = Image.new("RGB", (100, 50), (100, 100, 100))
    result = crop_square(img)
    assert result.size == (50, 50)


def test_crop_square_taller_than_wide():
    img = Image.new("RGB", (50, 100), (100, 100, 100))
    result = crop_square(img)
    assert result.size == (50, 50)


def test_quantize_image_returns_ndarray():
    img = Image.new("RGB", (100, 100), (128, 128, 128))
    result = quantize_image(img, 10, 20)
    assert isinstance(result, np.ndarray)
    assert result.shape == (20, 10, 3)


def test_quantize_image_converts_non_rgb():
    img = Image.new("RGBA", (100, 100), (128, 128, 128, 255))
    result = quantize_image(img, 10, 20)
    assert result.shape == (20, 10, 3)


def test_quantize_image_single_color():
    img = Image.new("RGB", (100, 100), (200, 100, 50))
    result = quantize_image(img, 5, 10, palette_colors=1)
    # All pixels should be approximately the same color
    assert result.shape == (10, 5, 3)


def test_pixels_to_rows_returns_text_list():
    # Create a 2-row (4 pixel tall) x 3 wide pixel array
    px = np.zeros((4, 3, 3), dtype=np.uint8)
    px[:] = 128
    rows = pixels_to_rows(px, 3, 2)
    assert len(rows) == 2


def test_pixels_to_rows_single_pixel():
    px = np.array([[[255, 0, 0], [0, 255, 0]]], dtype=np.uint8)
    # Need 2 rows tall (4 pixel rows)
    px = np.zeros((4, 2, 3), dtype=np.uint8)
    px[0, 0] = [255, 0, 0]
    px[1, 0] = [0, 255, 0]
    px[0, 1] = [255, 0, 0]
    px[1, 1] = [0, 255, 0]
    rows = pixels_to_rows(px, 2, 2)
    assert len(rows) == 2


def test_pixels_to_rows_all_same_color_one_span():
    px = np.full((2, 3, 3), 128, dtype=np.uint8)
    rows = pixels_to_rows(px, 3, 1)
    assert len(rows) == 1
    # Single span: one append call for the entire width
    assert len(rows[0]._spans) == 1


def test_image_to_rows_none_input():
    assert image_to_rows(None, 10, 5) == []


def test_image_to_rows_valid_image():
    img = Image.new("RGB", (100, 100), (128, 128, 128))
    rows = image_to_rows(img, 10, 5)
    assert len(rows) == 5
