"""
Runtime hook: set TCL_LIBRARY / TK_LIBRARY to our bundled copies.
Only activates when init.tcl / tk.tcl are physically present so we
never redirect Tcl to an empty folder.
"""
import sys
import os

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _mp  = sys._MEIPASS
    _tcl = os.path.join(_mp, "tcl_lib")
    _tk  = os.path.join(_mp, "tk_lib")
    if os.path.isfile(os.path.join(_tcl, "init.tcl")):
        os.environ["TCL_LIBRARY"] = _tcl
    if os.path.isfile(os.path.join(_tk, "tk.tcl")):
        os.environ["TK_LIBRARY"] = _tk
