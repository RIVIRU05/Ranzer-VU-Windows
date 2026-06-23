"""
Runtime hook: tell Tcl/Tk where to find its library files inside the bundle.
PyInstaller 6.x places bundled data under _internal/ but doesn't always set
TCL_LIBRARY / TK_LIBRARY, causing the "Can't find a usable init.tcl" crash.
"""
import sys
import os

if hasattr(sys, "_MEIPASS"):
    _mp = sys._MEIPASS
    _tcl = os.path.join(_mp, "_tcl_data")
    _tk  = os.path.join(_mp, "_tk_data")
    if os.path.isdir(_tcl):
        os.environ.setdefault("TCL_LIBRARY", _tcl)
    if os.path.isdir(_tk):
        os.environ.setdefault("TK_LIBRARY", _tk)
