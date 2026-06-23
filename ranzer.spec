# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for RANZER Windows — one-folder bundle.
# Run via: build_exe.bat  (do NOT run directly unless you know what you're doing)

import sys
import os
import glob

block_cipher = None

# Collect Tcl/Tk library data files.
# PyInstaller 6.x often fails to auto-bundle these, causing the
# "Can't find a usable init.tcl" crash at startup.
_tcl_root   = os.path.join(sys.prefix, "tcl")
_tcl_dirs   = sorted(glob.glob(os.path.join(_tcl_root, "tcl[0-9]*")))
_tk_dirs    = sorted(glob.glob(os.path.join(_tcl_root, "tk[0-9]*")))
_extra_datas = []
if _tcl_dirs:
    _extra_datas.append((_tcl_dirs[-1], "_tcl_data"))
if _tk_dirs:
    _extra_datas.append((_tk_dirs[-1],  "_tk_data"))

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
