from PIL import Image, ImageDraw, ImageFont

FONT_SIZE = 60


def _load_font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def render_week_icon(week, light_taskbar, size=64):
    '''
    Draw the week number centered on a transparent square, always with the same
    font size, black on a light taskbar and white on a dark one.
    '''
    color = "black" if light_taskbar else "white"
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.text((size / 2, size / 2), str(week), font=_load_font(FONT_SIZE), fill=color, anchor="mm")
    return image
