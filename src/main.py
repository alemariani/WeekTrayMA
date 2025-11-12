import threading
import time
from PIL import Image, ImageDraw, ImageFont
import pystray

import CalendarApp
import utils

def create_image(text, background_color, font_color):
    width, height = 64, 64
    image = Image.new('RGBA', (width, height), background_color)
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except IOError:
        font = ImageFont.load_default()
    draw.text((width/2, height/2), text, font=font, fill=font_color, anchor='mm')

    return image

def on_exit(icon, item):
    icon.stop()

def on_left_click(icon):
    icon.app.show()

def window_thread(icon):
    icon.app = CalendarApp.CalendarApp()
    icon.app.mainloop()

def update_icon(icon):
    digits_text = f'{icon.week}'
    font_color = 'black' if icon.theme == 'Light' else 'white'
    icon.icon = create_image(digits_text, (0, 0, 0, 0), font_color)

def init_trayicon():
    icon = pystray.Icon('WeekTrayAM')
    icon.title = 'WeekTrayAM'
    icon.week = utils.get_current_week()
    icon.theme = utils.get_windows_system_theme()
    icon.update = update_icon
    icon.menu = pystray.Menu(   \
        pystray.MenuItem('Open Calendar', on_left_click, default=True, visible=False),  \
        pystray.MenuItem('Quit', on_exit))
    
    return icon

def icon_updating_thread(icon):
    while True:
        current_week = utils.get_current_week()
        theme = utils.get_windows_system_theme()
        if current_week != icon.week or theme != icon.theme:
            icon.week = current_week
            icon.theme = theme
            icon.update(icon)

        time.sleep(60)  # run every 60 seconds

def main():
    trayicon = init_trayicon()
    trayicon.update(trayicon) # Initial icon update

    threading.Thread(target=window_thread, args=(trayicon, ), daemon=True).start()
    trayicon.run_detached()
    threading.Thread(target=icon_updating_thread, args=(trayicon,), daemon=True).start()

if __name__ == "__main__":
    main()