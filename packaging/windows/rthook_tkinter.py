"""
Runtime hook: set TCL_LIBRARY / TK_LIBRARY to our bundled copies.
Uses "tcl_lib"/"tk_lib" folder names (NOT "_tcl_data"/"_tk_data") so
PyInstaller's own _tkinter hook cannot overwrite them.
Force-assigns rather than setdefault so we always win.
"""
import sys
import os

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _mp  = sys._MEIPASS
    _tcl = os.path.join(_mp, "tcl_lib")
    _tk  = os.path.join(_mp, "tk_lib")
    if os.path.isdir(_tcl):
        os.environ["TCL_LIBRARY"] = _tcl
    if os.path.isdir(_tk):
        os.environ["TK_LIBRARY"] = _tk
