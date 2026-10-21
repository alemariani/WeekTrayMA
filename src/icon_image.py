from PIL import Image, ImageDraw, ImageFont

PADDING = 2


def _load_font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def render_week_icon(week, light_taskbar, size=64):
    '''
    Draw the week number as large as possible on a transparent square,
    black on a light taskbar and white on a dark one.
    '''
    text = str(week)
    color = "black" if light_taskbar else "white"
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    max_extent = size - 2 * PADDING
    font_size = size
    while True:
        font = _load_font(font_size)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        if (right - left <= max_extent and bottom - top <= max_extent) or font_size <= 1:
            break
        font_size -= 1

    # center the ink box, not the font's line box
    x = (size - (right - left)) / 2 - left
    y = (size - (bottom - top)) / 2 - top
    draw.text((x, y), text, font=font, fill=color)
    return image
