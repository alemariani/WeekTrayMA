import datetime
import time


def get_current_week():
    return datetime.date.today().isocalendar()[1]

def week_monitoring_thread(icon):
    while True:
        week = get_current_week()
        if week != icon.week:
            icon.week = week
            icon.update(icon)

        time.sleep(5)  # run every 60 seconds
