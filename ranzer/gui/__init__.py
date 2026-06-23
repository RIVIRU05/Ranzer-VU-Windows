import os
import sys


def _gui_resource(filename: str) -> str:
    """
    Resolve a GUI asset path that works in both dev and a PyInstaller bundle.

    PyInstaller 6+ sets sys._MEIPASS to the _internal/ dir in both
    one-file and one-folder modes. PyInstaller 5 one-folder doesn't set it,
    so we fall back to the directory containing the executable.
    Dev mode: resolve relative to this __init__.py file.
    """
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.realpath(sys.executable)))
        return os.path.join(base, filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
