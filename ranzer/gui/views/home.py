"""RANZER GUI - Home View"""

import tkinter as tk
from ranzer.gui import theme as T


class HomeView(tk.Frame):
    def __init__(self, parent, main_win):
        super().__init__(parent, bg=T.BG)
        self._main = main_win
        self._build()

    def _build(self):
        centre = tk.Frame(self, bg=T.BG)
        centre.place(relx=0.5, rely=0.44, anchor="center")

        logo_img = T.load_logo(96, 96)
        if logo_img:
            lbl = tk.Label(centre, image=logo_img, bg=T.BG)
            lbl.image = logo_img
            lbl.pack(pady=(0, 16))
        else:
            canvas = tk.Canvas(centre, width=80, height=80,
                               bg=T.BG, highlightthickness=0)
            canvas.pack(pady=(0, 16))
            canvas.create_oval(2, 2, 78, 78, fill=T.BLUE, outline="")
            canvas.create_text(40, 40, text="R", fill=T.WHITE,
                               font=(T.FONT_FAMILY, 30, "bold"))

        tk.Label(centre, text="RANZER",
                 bg=T.BG, fg=T.TEXT,
                 font=(T.FONT_FAMILY, 24, "bold")).pack()
        tk.Label(centre, text="Ransomware Detection System",
                 bg=T.BG, fg=T.TEXT_MUTED,
                 font=T.FONT_SMALL).pack(pady=(2, 24))

        tk.Label(centre, text="Monitoring Active",
                 bg=T.BG, fg=T.GREEN,
                 font=(T.FONT_FAMILY, 13, "bold")).pack()
        tk.Label(centre,
                 text="Navigate using the sidebar to view the\ndashboard, alerts, or system actions.",
                 bg=T.BG, fg=T.TEXT_MUTED,
                 font=T.FONT_BODY, justify="center").pack(pady=(6, 26))

        tk.Button(centre, text="▶  Go to Dashboard",
                  bg=T.BLUE, fg=T.WHITE, relief="flat",
                  font=(T.FONT_FAMILY, 11, "bold"), cursor="hand2",
                  padx=32, pady=10,
                  activebackground=T.BLUE_DARK, activeforeground=T.WHITE,
                  command=lambda: self._main.navigate("dashboard")).pack(fill="x")

    def on_show(self):
        pass

    def on_event(self, kind, event):
        pass
