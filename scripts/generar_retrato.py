#!/usr/bin/env python3
"""
Genera assets/banner.svg con un retrato de puntos (dithering Floyd-Steinberg,
recorrido serpentine) que rota entre varias imágenes.

Uso:
  python scripts/generar_retrato.py photos/foto.png "text:{ JL }" "text:</>"

Cada argumento es una imagen o un texto ("text:..."). Se muestran en ciclo.
Requiere: pip install pillow numpy
"""
import sys, random, pathlib
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "assets" / "banner.template.svg"
OUTPUT = ROOT / "assets" / "banner.svg"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"  # cambia si estás en Windows: C:/Windows/Fonts/consolab.ttf

W, H = 200, 227          # resolución de la rejilla de puntos
PANEL_X, PANEL_Y, PANEL_W, PANEL_H = 40, 90, 308, 196
CYCLE = 12               # segundos que dura el ciclo completo
PINK, DIM = "#F78CA0", "#5B6F91"
GAMMA = 1.6              # súbelo (2.0) para menos puntos de fondo, bájalo (1.0) para más detalle

def load_frame(spec):
    if spec.startswith("text:"):
        txt = spec[5:]
        img = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(img)
        size = int(H * 0.5)
        font = ImageFont.truetype(FONT, size)
        while d.textlength(txt, font=font) > W * 0.9 and size > 10:
            size -= 2
            font = ImageFont.truetype(FONT, size)
        l, t, r, b = d.textbbox((0, 0), txt, font=font)
        d.text(((W - (r - l)) / 2 - l, (H - (b - t)) / 2 - t), txt, font=font, fill=255)
        return img
    img = Image.open(spec).convert("L")
    img = ImageOps.fit(img, (W, H), method=Image.LANCZOS, centering=(0.5, 0.35))
    img = ImageOps.autocontrast(img, cutoff=2)
    return img.point(lambda v: int(255 * (v / 255) ** GAMMA))  # oscurece fondos para que resalte el rostro

def dither_serpentine(img):
    """Floyd-Steinberg con recorrido serpentine (izq->der, luego der->izq)."""
    a = np.array(img, dtype=np.float32)
    h, w = a.shape
    pts = []
    for y in range(h):
        d = 1 if y % 2 == 0 else -1
        xs = range(w) if d == 1 else range(w - 1, -1, -1)
        for x in xs:
            old = a[y, x]
            new = 255.0 if old >= 128 else 0.0
            err = old - new
            if 0 <= x + d < w: a[y, x + d] += err * 7 / 16
            if y + 1 < h:
                if 0 <= x - d < w: a[y + 1, x - d] += err * 3 / 16
                a[y + 1, x] += err * 5 / 16
                if 0 <= x + d < w: a[y + 1, x + d] += err * 1 / 16
            if new == 255.0:
                pts.append((x, y))
    return pts

def frame_svg(idx, pts, n):
    rnd = random.Random(idx)
    main, dim = [], []
    for x, y in pts:
        (dim if rnd.random() < 0.15 else main).append(f"M{x} {y}h0")
    return (f'<g class="fr" style="animation-delay:{idx * CYCLE / n:.2f}s">'
            f'<path d="{"".join(main)}" stroke="{PINK}"/>'
            f'<path d="{"".join(dim)}" stroke="{DIM}"/></g>')

def main(specs):
    frames, total = [], 0
    for i, spec in enumerate(specs):
        pts = dither_serpentine(load_frame(spec))
        total = max(total, len(pts))
        frames.append(frame_svg(i, pts, len(specs)))
        print(f"{spec}: {len(pts)} puntos")
    n = len(specs)
    s = min(PANEL_W / W, PANEL_H / H)
    tx = PANEL_X + (PANEL_W - W * s) / 2
    vis = 100 / n
    css = (f".fr{{opacity:0;fill:none;stroke-width:1.2;stroke-linecap:round;"
           f"animation:cyc {CYCLE}s infinite}}.fr:first-child{{opacity:1}}"
           f"@keyframes cyc{{0%{{opacity:0}}2%{{opacity:1}}{vis - 2:.2f}%{{opacity:1}}"
           f"{vis:.2f}%{{opacity:0}}100%{{opacity:0}}}}")
    group = (f'<style>{css}</style>'
             f'<g transform="translate({tx:.2f} {PANEL_Y}) scale({s:.4f})">' + "".join(frames) + "</g>")
    svg = TEMPLATE.read_text(encoding="utf-8")
    svg = svg.replace("<!--DOTS-->", group).replace("{{LABEL}}", f"PTS {total} · FS/SERPENTINE")
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"Listo: {OUTPUT} ({OUTPUT.stat().st_size / 1024:.0f} KB)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
