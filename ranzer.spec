# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for RANZER Windows — one-folder bundle.
# Run via: build_exe.bat  (do NOT run directly unless you know what you're doing)

import sys
import os

block_cipher = None

# Collect Tcl/Tk library data files.
# Ask Tcl's own interpreter where it lives — this works for any Python
# version or install location (standard, Microsoft Store, conda, etc.)
# and any Tcl version (8.6, 9.0, ...).
_extra_datas = []
try:
    import tkinter as _tk
    _interp = _tk.Tcl()
    _tcl_lib = _interp.eval("info library")   # e.g. C:/Python314/tcl/tcl8.6
    _tk_ver  = "{:.1f}".format(_tk.TkVersion) # e.g. "8.6"
    _tk_lib  = os.path.normpath(
        os.path.join(_tcl_lib, "..", "tk" + _tk_ver)
    )
    del _interp, _tk
    # Use "tcl_lib"/"tk_lib" — NOT "_tcl_data"/"_tk_data" (those are owned by
    # PyInstaller's internal _tkinter hook and get overwritten with empty dirs).
    if os.path.isdir(_tcl_lib):
        _extra_datas.append((_tcl_lib, "tcl_lib"))
        print(f"[spec] Tcl library: {_tcl_lib}")
    if os.path.isdir(_tk_lib):
        _extra_datas.append((_tk_lib, "tk_lib"))
        print(f"[spec]  Tk library: {_tk_lib}")
except Exception as _e:
    print(f"[spec] WARNING: Could not locate Tcl/Tk data: {_e}")

a = Analysis(
    ["ranzer/__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("ranzer/gui/logo.png",          "."),
        ("ranzer/gui/image.png",         "."),
        ("ranzer/gui/logo_30.png",       "."),
        ("ranzer/gui/logo_30_blue.png",  "."),
        ("ranzer/gui/logo_76.png",       "."),
        ("ranzer/gui/image_header.png",  "."),
    ] + _extra_datas,
    hiddenimports=[
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "psutil",
        "watchdog",
        "watchdog.observers",
        "watchdog.observers.winapi",
        "watchdog.events",
        "PIL",
        "PIL.Image",
        "PIL.ImageTk",
        "ranzer.core",
        "ranzer.core.engine",
        "ranzer.core.entropy_monitor",
        "ranzer.core.honey_file_engine",
        "ranzer.core.process_tracker",
        "ranzer.core.file_watcher",
        "ranzer.core.threat_correlator",
        "ranzer.core.alert_handler",
        "ranzer.gui",
        "ranzer.gui.app",
        "ranzer.gui.landing",
        "ranzer.gui.setup_window",
        "ranzer.gui.main_window",
        "ranzer.gui.theme",
        "ranzer.gui.views",
        "ranzer.gui.views.home",
        "ranzer.gui.views.dashboard",
        "ranzer.gui.views.alerts",
        "ranzer.gui.views.actions",
    ],
    hookspath=[],
    runtime_hooks=["packaging/windows/rthook_tkinter.py"],
    excludes=["matplotlib", "numpy", "scipy", "pandas", "IPython"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ranzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    argv_emulation=False,
    target_arch=None,
    icon="packaging\\windows\\ranzer.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ranzer",
)
