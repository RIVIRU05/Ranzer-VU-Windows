"""
RANZER GUI — Entry point.
Launch with:  python3 -m ranzer.cli gui
"""

import tkinter as tk
from ranzer.gui.landing import LandingPage
from ranzer.gui import theme as T


def launch_gui(prefill_dirs=None):
    root = tk.Tk()
    root.withdraw()  # hide root; LandingPage owns the first visible window
    icon = T.load_logo(32, 32, "#FFFFFF")
    if icon:
        root.iconphoto(True, icon)  # True = propagate to all Toplevels
    app = LandingPage(root, prefill_dirs=prefill_dirs or [])
    root.mainloop()
