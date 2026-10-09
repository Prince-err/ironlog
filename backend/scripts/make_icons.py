"""Generate Iron Log PWA icons.

Draws a dumbbell glyph on a dark rounded square with a lime accent bar.
Run from repo root or gym/backend:  python scripts/make_icons.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[2] / "frontend" / "public"
SIZES = [192, 512]

BG = (9, 9, 11)        # --background #09090b
ACCENT = (212, 255, 63)  # --accent #d4ff3f
SURFACE = (22, 22, 26)   # --surface-2


def rounded_square(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=BG)
    return img


def draw_glyph(img: Image.Image) -> Image.Image:
    size = img.width
    d = ImageDraw.Draw(img)
    s = size / 512  # design space

    # accent bar across the top
    d.rounded_rectangle(
        [64 * s, 74 * s, 448 * s, 106 * s], radius=16 * s, fill=ACCENT
    )

    # dumbbell: two plates + bar
    cy = 286 * s
    plate_w, plate_h = 46 * s, 150 * s
    inner_w, inner_h = 34 * s, 108 * s
    # outer plates
    d.rounded_rectangle([96 * s, cy - plate_h / 2, 96 * s + plate_w, cy + plate_h / 2],
                        radius=14 * s, fill=ACCENT)
    d.rounded_rectangle([416 * s - plate_w, cy - plate_h / 2, 416 * s, cy + plate_h / 2],
                        radius=14 * s, fill=ACCENT)
    # inner plates
    d.rounded_rectangle([150 * s, cy - inner_h / 2, 150 * s + inner_w, cy + inner_h / 2],
                        radius=10 * s, fill=ACCENT)
    d.rounded_rectangle([416 * s - inner_w - 54 * s, cy - inner_h / 2,
                         416 * s - 54 * s, cy + inner_h / 2],
                        radius=10 * s, fill=ACCENT)
    # bar
    d.rounded_rectangle([196 * s, cy - 11 * s, 316 * s, cy + 11 * s],
                        radius=11 * s, fill=ACCENT)

    # base line
    d.rounded_rectangle([96 * s, 420 * s, 416 * s, 444 * s],
                        radius=12 * s, fill=SURFACE)
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        img = rounded_square(size)
        draw_glyph(img)
        path = OUT / f"icon-{size}.png"
        img.save(path, "PNG")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
