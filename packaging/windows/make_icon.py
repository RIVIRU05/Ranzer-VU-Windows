"""
Generates packaging/windows/ranzer.ico from ranzer/gui/logo.png.
Run from the Ranzer-Windows root:  python packaging/windows/make_icon.py
"""
import os
import sys
from PIL import Image

LOGO_SRC  = os.path.join("ranzer", "gui", "logo.png")
ICON_OUT  = os.path.join("packaging", "windows", "ranzer.ico")
PADDING   = 0.20   # 20% whitespace around the logo on each side
BG_COLOR  = (255, 255, 255)   # solid white background

SIZES = [256, 128, 64, 48, 32, 16]

def make_icon():
    if not os.path.exists(LOGO_SRC):
        print(f"ERROR: logo not found at {LOGO_SRC}")
        sys.exit(1)

    # Load logo with full alpha
    logo = Image.open(LOGO_SRC).convert("RGBA")
    lw, lh = logo.size

    # Square canvas size = logo's longest side + padding on all sides
    inner = max(lw, lh)
    pad   = int(inner * PADDING)
    sq    = inner + pad * 2

    # Flat white RGB canvas (no alpha = no transparency surprises in ICO)
    canvas = Image.new("RGB", (sq, sq), BG_COLOR)

    # Composite logo onto white using its own alpha channel as mask
    r, g, b, alpha = logo.split()
    logo_rgb = Image.merge("RGB", (r, g, b))
    x = (sq - lw) // 2
    y = (sq - lh) // 2
    canvas.paste(logo_rgb, (x, y), mask=alpha)

    # Resize to each icon size with high-quality LANCZOS
    frames = [canvas.resize((s, s), Image.LANCZOS) for s in SIZES]

    # Save: first frame is the largest (256), rest appended in descending order
    frames[0].save(
        ICON_OUT,
        format="ICO",
        append_images=frames[1:]
    )

    print(f"Icon saved: {ICON_OUT}")
    print(f"  Source : {lw}x{lh} RGBA logo")
    print(f"  Canvas : {sq}x{sq} white square")
    print(f"  Sizes  : {', '.join(str(s) for s in SIZES)}")

if __name__ == "__main__":
    make_icon()
