from icon_image import render_week_icon


def ink_height(week):
    left, top, right, bottom = render_week_icon(week, light_taskbar=True).getbbox()
    return bottom - top


def test_digit_size_is_the_same_for_every_week():
    # flat-edged digits only: round ones (3, 5, 8...) overshoot by a pixel by design
    heights = {ink_height(week) for week in (1, 4, 7, 11, 14, 17, 41, 44, 47)}
    assert len(heights) == 1


def opaque_pixels(image):
    pixels = image.load()
    width, height = image.size
    return [pixels[x, y] for x in range(width) for y in range(height) if pixels[x, y][3] == 255]


def test_digit_color_follows_taskbar():
    dark = render_week_icon(42, light_taskbar=False)
    light = render_week_icon(42, light_taskbar=True)
    assert max(p[0] for p in opaque_pixels(dark)) == 255
    assert min(p[0] for p in opaque_pixels(light)) == 0
