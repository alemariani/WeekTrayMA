from icon_image import render_week_icon


def test_two_digit_weeks_fit_with_padding():
    for week in (1, 8, 48, 53, 88):
        bbox = render_week_icon(week, light_taskbar=True).getbbox()
        assert bbox is not None
        left, top, right, bottom = bbox
        assert left >= 2 and top >= 2 and right <= 62 and bottom <= 62


def opaque_pixels(image):
    pixels = image.load()
    width, height = image.size
    return [pixels[x, y] for x in range(width) for y in range(height) if pixels[x, y][3] == 255]


def test_digit_color_follows_taskbar():
    dark = render_week_icon(42, light_taskbar=False)
    light = render_week_icon(42, light_taskbar=True)
    assert max(p[0] for p in opaque_pixels(dark)) == 255
    assert min(p[0] for p in opaque_pixels(light)) == 0
