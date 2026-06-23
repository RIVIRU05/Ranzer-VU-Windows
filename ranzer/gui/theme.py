"""Shared design tokens for the RANZER GUI — polished light theme."""

import os

# ── Colours ───────────────────────────────────────────────────────────────────
BLUE        = "#2563EB"
BLUE_DARK   = "#1D4ED8"
BLUE_LIGHT  = "#EFF6FF"
BLUE_GLOW   = "#2563EB"

SIDEBAR     = "#1E293B"
SIDEBAR_ACT = "#2563EB"

BG          = "#F1F5F9"
CARD        = "#FFFFFF"
CARD2       = "#F8FAFC"
BORDER      = "#E2E8F0"
BORDER2     = "#CBD5E1"

TEXT        = "#0F172A"
TEXT_MUTED  = "#64748B"
WHITE       = "#FFFFFF"

SEV_CRITICAL = "#EF4444"
SEV_HIGH     = "#F97316"
SEV_MEDIUM   = "#F59E0B"
SEV_LOW      = "#3B82F6"
SEV_NONE     = "#94A3B8"
GREEN        = "#16A34A"
RED_BTN      = "#DC2626"

# Row background tints for the System Actions table
ROW_CRITICAL_BG   = "#FEF2F2"   # light red
ROW_HIGH_BG       = "#FFF7ED"   # light orange
ROW_LOW_BG        = "#EFF6FF"   # light blue
ROW_TERMINATED_BG = "#FFFBEB"   # light amber
ROW_ENDED_BG      = "#F8FAFC"   # very light gray

FONT_FAMILY  = "Helvetica"
FONT_HEADING = (FONT_FAMILY, 16, "bold")
FONT_SUBHEAD = (FONT_FAMILY, 12, "bold")
FONT_BODY    = (FONT_FAMILY, 10)
FONT_SMALL   = (FONT_FAMILY, 9)
FONT_MONO    = ("Courier", 9)


def severity_color(sev: str) -> str:
    return {
        "CRITICAL": SEV_CRITICAL,
        "HIGH":     SEV_HIGH,
        "MEDIUM":   SEV_MEDIUM,
        "LOW":      SEV_LOW,
    }.get(sev.upper(), SEV_NONE)


# ── Logo loader ───────────────────────────────────────────────────────────────
import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if getattr(_sys, "frozen", False):
    _HERE = getattr(_sys, "_MEIPASS", os.path.dirname(os.path.realpath(_sys.executable)))
_LOGO_PNG = os.path.join(_HERE, "logo.png")

_logo_cache: dict = {}


def load_logo(width: int = 64, height: int = 64, bg: str = WHITE):
    """Return a PhotoImage of the Ranzer logo at the given size, or None."""
    key = (width, height, bg)
    if key in _logo_cache:
        return _logo_cache[key]

    # Try PIL first — best quality with transparency compositing
    try:
        from PIL import Image, ImageTk
        img = Image.open(_LOGO_PNG).convert("RGBA")
        r, g, b = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
        background = Image.new("RGBA", img.size, (r, g, b, 255))
        background.paste(img, mask=img.split()[3])
        background = background.resize((width, height), Image.LANCZOS)
        photo = ImageTk.PhotoImage(background)
        _logo_cache[key] = photo
        return photo
    except Exception as _e:
        import sys as _s
        print(f"[RANZER] PIL logo load failed: {_e} | path={_LOGO_PNG}", file=_s.stderr)

    # Fallback — load pre-sized PNG (no PIL, no scaling, stays sharp)
    try:
        import tkinter as _tk
        if width <= 30 and bg == BLUE:
            fallback = os.path.join(_HERE, "logo_30_blue.png")
        elif width <= 30:
            fallback = os.path.join(_HERE, "logo_30.png")
        else:
            fallback = os.path.join(_HERE, "logo_76.png")
        photo = _tk.PhotoImage(file=fallback)
        _logo_cache[key] = photo
        return photo
    except Exception as _e:
        import sys as _s
        print(f"[RANZER] tk logo fallback failed: {_e} | path={fallback}", file=_s.stderr)

    return None
