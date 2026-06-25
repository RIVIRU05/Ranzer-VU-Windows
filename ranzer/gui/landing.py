"""RANZER GUI - Landing Page"""

import os
import tkinter as tk
from ranzer.gui import theme as T

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if getattr(_sys, "frozen", False):
    _HERE = getattr(_sys, "_MEIPASS", os.path.dirname(os.path.realpath(_sys.executable)))

def _load_uni_logo(height: int = 32, bg: str = T.CARD):
    path = os.path.join(_HERE, "image.png")

    # Try PIL first - best quality with transparency compositing
    try:
        from PIL import Image, ImageTk
        img = Image.open(path).convert("RGBA")
        ratio = height / img.height
        w = int(img.width * ratio)
        img = img.resize((w, height), Image.LANCZOS)
        r, g, b = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
        background = Image.new("RGBA", img.size, (r, g, b, 255))
        background.paste(img, mask=img.split()[3])
        return ImageTk.PhotoImage(background)
    except Exception as _e:
        import sys as _s
        print(f"[RANZER] PIL uni-logo load failed: {_e} | path={path}", file=_s.stderr)

    # Fallback - load pre-sized composited PNG (no PIL, no scaling needed)
    try:
        fallback = os.path.join(_HERE, "image_header.png")
        photo = tk.PhotoImage(file=fallback)
        return photo
    except Exception as _e:
        import sys as _s
        print(f"[RANZER] tk uni-logo fallback failed: {_e} | path={fallback}", file=_s.stderr)

    return None


class LandingPage(tk.Toplevel):
    def __init__(self, root, prefill_dirs=None):
        super().__init__(root)
        self._root = root
        self._prefill_dirs = prefill_dirs or []
        self.title("RANZER")
        self.resizable(False, False)
        self.configure(bg=T.BG)
        self._center(480, 450)
        self.protocol("WM_DELETE_WINDOW", self._quit)
        self._build()

    def _center(self, w, h):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build(self):
        # Header
        header = tk.Frame(self, bg=T.BLUE, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Uni logo - right side, packed first so it claims the space before left items
        uni_img = _load_uni_logo(height=40, bg=T.BLUE)
        if uni_img:
            uni_lbl = tk.Label(header, image=uni_img, bg=T.BLUE)
            uni_lbl.image = uni_img
            uni_lbl.pack(side="right", padx=(0, 16), pady=8)

        logo_img = T.load_logo(30, 30, T.BLUE)
        if logo_img:
            lbl = tk.Label(header, image=logo_img, bg=T.BLUE)
            lbl.image = logo_img
            lbl.pack(side="left", padx=(16, 8), pady=13)

        tk.Label(header, text="RANZER  –  Ransomware Detection",
                 bg=T.BLUE, fg=T.WHITE,
                 font=(T.FONT_FAMILY, 13, "bold")).pack(side="left", pady=17)

        # Body
        body = tk.Frame(self, bg=T.BG, padx=36, pady=16)
        body.pack(fill="both", expand=True)

        # Logo
        logo_img2 = T.load_logo(76, 76, T.BG)
        if logo_img2:
            lbl2 = tk.Label(body, image=logo_img2, bg=T.BG)
            lbl2.image = logo_img2
            lbl2.pack(pady=(4, 10))
        else:
            canvas = tk.Canvas(body, width=68, height=68, bg=T.BG, highlightthickness=0)
            canvas.pack(pady=(4, 10))
            canvas.create_oval(2, 2, 66, 66, fill=T.BLUE, outline="")
            canvas.create_text(34, 34, text="R", fill=T.WHITE,
                               font=(T.FONT_FAMILY, 24, "bold"))

        tk.Label(body, text="Welcome to RANZER",
                 bg=T.BG, fg=T.TEXT,
                 font=(T.FONT_FAMILY, 17, "bold")).pack()
        tk.Label(body, text="Select an option to begin ransomware detection",
                 bg=T.BG, fg=T.TEXT_MUTED, font=T.FONT_BODY).pack(pady=(4, 18))

        self._card(body,
                   title="▶   Start  (default - honey files enabled)",
                   subtitle="Begin monitoring with recommended settings",
                   command=self._start_default,
                   primary=True)

        tk.Frame(body, bg=T.BORDER, height=1).pack(fill="x", pady=10)

        self._card(body,
                   title="⚙   Advanced",
                   subtitle="Configure entropy threshold, auto-terminate & more",
                   command=self._start_advanced,
                   primary=False)

        # Footer
        footer = tk.Frame(self, bg=T.CARD, padx=16, pady=6)
        footer.pack(fill="x", side="bottom")
        tk.Label(footer, text="RANZER v1.0  •  Endpoint Defense System  🇱🇰",
                 bg=T.CARD, fg=T.TEXT_MUTED, font=T.FONT_SMALL).pack(anchor="w")

    def _card(self, parent, title, subtitle, command, primary=False):
        bg   = T.BLUE      if primary else T.CARD
        fg   = T.WHITE     if primary else T.TEXT
        sfg  = "#BFDBFE"   if primary else T.TEXT_MUTED
        bord = T.BLUE_DARK if primary else T.BORDER
        hov  = T.BLUE_DARK if primary else T.BLUE_LIGHT

        card = tk.Frame(parent, bg=bg, cursor="hand2",
                        highlightbackground=bord, highlightthickness=1)
        card.pack(fill="x", pady=3, ipady=6)

        inner = tk.Frame(card, bg=bg, padx=18)
        inner.pack(fill="x")
        tk.Label(inner, text=title, bg=bg, fg=fg,
                 font=(T.FONT_FAMILY, 11, "bold")).pack(anchor="w", pady=(10, 2))
        tk.Label(inner, text=subtitle, bg=bg, fg=sfg,
                 font=T.FONT_SMALL).pack(anchor="w", pady=(0, 10))

        def _enter(e):
            card.configure(bg=hov, highlightbackground=T.BLUE)
            inner.configure(bg=hov)
            for w in inner.winfo_children():
                w.configure(bg=hov)

        def _leave(e):
            card.configure(bg=bg, highlightbackground=bord)
            inner.configure(bg=bg)
            for w in inner.winfo_children():
                w.configure(bg=bg)

        for widget in (card, inner, *inner.winfo_children()):
            widget.bind("<Button-1>", lambda e, cmd=command: cmd())
            widget.bind("<Enter>", _enter)
            widget.bind("<Leave>", _leave)

    def _start_default(self):
        from ranzer.gui.setup_window import SetupWindow
        self.withdraw()
        SetupWindow(self._root, advanced=False,
                    prefill_dirs=self._prefill_dirs, on_back=self._show)

    def _start_advanced(self):
        from ranzer.gui.setup_window import SetupWindow
        self.withdraw()
        SetupWindow(self._root, advanced=True,
                    prefill_dirs=self._prefill_dirs, on_back=self._show)

    def _show(self):
        self.deiconify()

    def _quit(self):
        self._root.destroy()
