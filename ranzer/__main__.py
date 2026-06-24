import sys as _sys
import os as _os

# When running as a PyInstaller bundle, point Tcl/Tk to the bundled script
# libraries BEFORE anything imports tkinter.  PyInstaller's own _tkinter hook
# can overwrite TCL_LIBRARY with an empty folder; doing it here (after all
# hooks) wins the race.
if getattr(_sys, "frozen", False) and hasattr(_sys, "_MEIPASS"):
    _mp = _sys._MEIPASS
    _tcl = _os.path.join(_mp, "tcl_lib")
    _tk  = _os.path.join(_mp, "tk_lib")
    if _os.path.isdir(_tcl):
        _os.environ["TCL_LIBRARY"] = _tcl
    if _os.path.isdir(_tk):
        _os.environ["TK_LIBRARY"] = _tk

from ranzer.cli import main
main()
