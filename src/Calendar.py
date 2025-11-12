import customtkinter as ctk
import calendar
from datetime import datetime

class Calendar(ctk.CTkFrame):
    _default_theme = {
        'font_family': 'Arial',
        'color_bg': ('#f9ecec', '#232234'),
        'color_bg2': ('#edc5c5', '#3e3c5d'),
        'color_accent': ('#E85F5C', '#00fefe'),
        'color_text': ('#020222', '#EEEEFF'),
        'color_text_muted': ('#73738c', '#686868'),
    }

    def __init__(self, master=None, theme=None):
        if theme is None:
            self.theme = self._default_theme
        super().__init__(master, fg_color=self.theme['color_bg'])

        self.init_ui()
        self.reset_month()

    def init_ui(self):
        self.winfo_toplevel().configure(fg_color=self.theme['color_bg'])
        
        for i in range(8):
            self.columnconfigure(i, weight = 1)
        self.rowconfigure(0, weight = 1)
        self.rowconfigure(1, weight = 7)
        
        # Create a frame for the header
        header_frame = ctk.CTkFrame(self, fg_color='transparent')
        header_frame.grid(row=0, column=0, columnspan=8, sticky='EW', pady=10)

        month_label = ctk.CTkLabel(header_frame, text="", font=(self.theme['font_family'], 16), text_color=self.theme['color_text'])
        month_label.pack(side="left", padx=10)
        self.month_label = month_label

        # Create navigation buttons
        next_button = ctk.CTkButton(header_frame, text=">>", width=30, command=self.next_month, text_color=self.theme['color_text'], fg_color='transparent', hover_color=self.theme['color_bg2'])
        next_button.pack(side="right", padx=4)
        
        prev_button = ctk.CTkButton(header_frame, text="<<", width=30, command=self.prev_month, text_color=self.theme['color_text'], fg_color='transparent', hover_color=self.theme['color_bg2'])
        prev_button.pack(side="right", padx=4)
        
        # Create a container frame to hold the month ui data diplayed
        month_container = ctk.CTkFrame(self, fg_color='transparent')
        month_container.grid(row=1, column=0, columnspan=8, sticky='EW')
        
        self.month_container = month_container
        # initial empty frame.
        # this is needed for month frame updating, since it destroys the old(this) frame and build a new one.
        month_frame = ctk.CTkFrame(month_container)
        
    def create_month_frame(self, parent, year, month):
        # Create the calendar
        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.itermonthdays4(year, month)
        # reshape in a list of weeks
        # each day is a tuple consisting of (year, month, day of the month, day of the week)
        month_days = list(month_days)
        month_days = [ month_days[x:x+7] for x in range(0, len(month_days), 7) ]
        
        month_frame = ctk.CTkFrame(parent, fg_color='transparent')
        for i in range(8):
            month_frame.columnconfigure(i, weight = 1)
        
        # Display the week headers
        headers = ["Wee", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for col, header in enumerate(headers):
            header_label = ctk.CTkLabel(month_frame, text=header, font=(self.theme['font_family'], 12), text_color=self.theme['color_text_muted'])
            header_label.grid(row=1, column=col, padx=5, pady=0, sticky='we')

        # Display the days and week numbers
        today = datetime.now()
        for row, week in enumerate(month_days, start=2):
            month_frame.rowconfigure(row, weight = 1)
            week_number = datetime(week[0][0], week[0][1], week[0][2]).isocalendar()[1]
            week_label = ctk.CTkLabel(month_frame, text=str(week_number), font=(self.theme['font_family'], 12), text_color=self.theme['color_text_muted'])
            week_label.grid(row=row, column=0, padx=5, pady=0)
            for col, day in enumerate(week, start=1):
                if  day[0] == today.year and day[1] == today.month and day[2] == today.day:
                    day_label = ctk.CTkLabel(month_frame, text=str(day[2]), font=(self.theme['font_family'], 12), fg_color=self.theme['color_accent'], text_color=self.theme['color_bg'], corner_radius=10)
                else:
                    if day[1] == month:
                        text_color = self.theme['color_text']
                    else:
                        text_color = self.theme['color_text_muted']
                    day_label = ctk.CTkLabel(month_frame, text=str(day[2]), font=(self.theme['font_family'], 12), text_color=text_color)
                day_label.grid(row=row, column=col, padx=5, pady=0, sticky='we')
        
        return month_frame
        
    def update_month_frame(self, animation_type):
        '''
        animation_type: 'RIGHT', 'LEFT', 'NONE'
        '''
        animation_speed = 20

        self.month_label.configure(text=f"{calendar.month_name[self.current_month]} {self.current_year}")
        new_frame = self.create_month_frame(self.month_container, self.current_year, self.current_month)
        
        # in the month_container frame there are 2 children: the current month and the new month.
        # at the end of the animation the current month (now old) is destroyed.
        # when clicking rapidly the arrow to change month (i.e. clicking a second time before the frame is destroyed),
        # there is a moment when the children are actually 3.
        # Thus, taking the [-2] child is needed instead of the [0].
        current_frame = self.month_container.winfo_children()[-2]

        current_frame.update_idletasks()
        new_frame.update_idletasks()
        
        width = current_frame.winfo_width()
        orig_width = width

        def slide():
            nonlocal width
            if width > animation_speed:
                width -= animation_speed
                if animation_type == 'LEFT':
                    current_frame.place(x=width - orig_width, y=0)
                    new_frame.place(x=width, y=0)
                else:
                    current_frame.place(x=orig_width - width, y=0)
                    new_frame.place(x=-width, y=0)
                self.after(10, slide)
            else:
                current_frame.destroy()
                new_frame.place(x=0, y=0, relwidth=1, relheight=1)

        if animation_type == 'LEFT':
            new_frame.place(x= orig_width, y=0, relwidth=1, relheight=1)
            slide()
        elif animation_type == 'RIGHT':
            new_frame.place(x= -orig_width, y=0, relwidth=1, relheight=1)
            slide()
        else:
            current_frame.destroy()
            new_frame.place(x=0, y=0, relwidth=1, relheight=1)
        
    
    def prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.update_month_frame('RIGHT')

    def next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.update_month_frame('LEFT')
    
    def set_month(self, year, month):
        self.current_month = month
        self.current_year = year
        self.update_month_frame('NONE')

    def reset_month(self):
        now = datetime.now()
        self.set_month(now.year, now.month)