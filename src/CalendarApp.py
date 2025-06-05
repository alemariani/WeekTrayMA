import customtkinter as ctk
import Calendar
from win32api import GetMonitorInfo, MonitorFromPoint

class CalendarApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.focusOutForOverrideredirect = False
        
        work_area = self.get_monitor_work_area_size()
        lenght = 300
        height = 200
        x = (work_area[2] - (lenght * self._get_window_scaling()) - 2)
        y = (work_area[3] - (height * self._get_window_scaling()) - 2)
        self.geometry('%dx%d+%d+%d'%(lenght, height, x, y))

        self.rowconfigure(0, weight = 1)
        self.columnconfigure(0, weight = 1)
        self.calendar_frame = Calendar.Calendar(self)
        self.calendar_frame.grid(row=0, column=0, sticky='NSWE')
        
        self.bind("<FocusOut>", self.on_focus_out)
        self.withdraw()
        
    def on_focus_out(self, event):
        if self.focusOutForOverrideredirect:
            self.focusOutForOverrideredirect = False
        else:
            self.withdraw()
        
    @staticmethod
    def get_monitor_work_area_size():
        primary_monitor = MonitorFromPoint((0,0))
        monitor_info = GetMonitorInfo(primary_monitor)
        work_area = monitor_info.get("Work")
        return work_area
    
    def show(self):
        self.after(0, self._show)

    def _show(self):
        self.calendar_frame.reset_month()
        #self.update_idletasks()
        self.deiconify()
        self.focus_force()


if __name__ == "__main__":
    app = CalendarApp()
    app.show()
    app.mainloop()
