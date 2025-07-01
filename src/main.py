import threading
from PIL import Image, ImageDraw, ImageFont
import pystray
from pystray import MenuItem as item
import datetime
import CalendarApp

def get_current_week():
    return datetime.date.today().isocalendar()[1]

def create_image2(text, background_color, font_color):
    width, height = 64, 64
    image = Image.new('RGBA', (width, height), background_color)
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except IOError:
        font = ImageFont.load_default()
    draw.text((width/2, height/2), text, font=font, fill=font_color, anchor='mm')

    return image

def create_image(text):
    #return create_image2(text, (255, 255, 255, 255), 'black')
    return create_image2(text, (0, 0, 0, 0), 'white')

def on_exit(icon, item):
    icon.stop()

def on_left_click(icon):
    icon.app.show()

def window_thread(icon):
    icon.app = CalendarApp.CalendarApp()
    icon.app.mainloop()

def update_icon(icon, item):
    week = get_current_week()
    digits_text = f'{week}'
    icon.icon = create_image(digits_text)

def main():
    icon = pystray.Icon('Week Number')
    icon.title = 'Week Number'
    update_icon(icon, None)
    icon.calendarThread = threading.Thread(target=window_thread, args=(icon, ))
    icon.calendarThread.daemon = True
    icon.calendarThread.start()
    icon.menu = pystray.Menu(   \
        item('Open Calendar', on_left_click, default=True, visible=False),  \
        item('Refresh', update_icon), \
        item('Quit', on_exit))

    threading.Thread(target=run_icon, args=(icon,)).start()

def run_icon(icon):
    icon.run()

if __name__ == "__main__":
    main()