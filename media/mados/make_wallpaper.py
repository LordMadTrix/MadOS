"""
MadOS - fond d'ecran "Braise" (PNG 2560x1440, LiberNT lit le PNG).
Sortie : modules/wallpapers/MadOS.png
"""
import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from mados_common import ACCENT, DESKTOP, MUTED, TREE, WHITE, font, mark

OUT = TREE / "modules" / "wallpapers" / "MadOS.png"


def add(a, b):
    return ImageChops.add(a, b)


def make(size=(2560, 1440), seed=7):
    W, H = size
    k = W / 1920                                   # echelle par rapport au dessin 1080p
    rnd = random.Random(seed)
    img = Image.new("RGB", size, DESKTOP)

    glow = Image.new("RGB", size, (0, 0, 0))
    d = ImageDraw.Draw(glow)
    for i in range(60, 0, -1):
        t = i / 60
        rad = int(1100 * k * t)
        col = (int(150 * (1 - t) ** 1.6), int(30 * (1 - t) ** 2.2), int(10 * (1 - t) ** 3))
        d.ellipse([W * 0.82 - rad, H * 1.05 - rad * 0.8, W * 0.82 + rad, H * 1.05 + rad * 0.8], fill=col)
    img = add(img, glow.filter(ImageFilter.GaussianBlur(60 * k)))

    ribbons = Image.new("RGB", size, (0, 0, 0))
    d = ImageDraw.Draw(ribbons)
    palette = [(239, 68, 68), (249, 115, 22), (185, 28, 28), (251, 146, 60)]
    for n in range(7):
        amp = rnd.uniform(60, 160) * k
        freq = rnd.uniform(0.0016, 0.0032) / k
        phase = rnd.uniform(0, math.tau)
        base = H * (0.55 + 0.06 * n)
        width = max(1, int(rnd.randint(2, 6) * k))
        dim = 0.35 + 0.65 * (n / 6)
        col = tuple(int(c * dim) for c in palette[n % len(palette)])
        pts = [(x, base + amp * math.sin(x * freq + phase) - 0.18 * x * (n % 3) / 3)
               for x in range(-20, W + 21, 8)]
        d.line(pts, fill=col, width=width, joint="curve")
    img = add(img, ribbons.filter(ImageFilter.GaussianBlur(18 * k)))
    img = add(img, ribbons.filter(ImageFilter.GaussianBlur(1.2 * k)))

    sparks = Image.new("RGB", size, (0, 0, 0))
    d = ImageDraw.Draw(sparks)
    for _ in range(320):
        x = rnd.gauss(W * 0.78, W * 0.18)
        y = rnd.uniform(H * 0.25, H)
        r = rnd.choice([1, 1, 1, 2, 2, 3]) * k
        a = rnd.uniform(0.3, 1.0) * (y / H)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(int(255 * a), int(150 * a), int(60 * a)))
    img = add(img, sparks.filter(ImageFilter.GaussianBlur(0.8 * k)))
    img = add(img, sparks.filter(ImageFilter.GaussianBlur(6 * k)))

    vig = Image.new("L", size, 0)
    d = ImageDraw.Draw(vig)
    for i in range(40):
        t = i / 40
        d.rectangle([W * t * 0.12, H * t * 0.12, W - W * t * 0.12, H - H * t * 0.12], fill=int(255 * (0.55 + 0.45 * t)))
    img = Image.composite(img, Image.new("RGB", size, (0, 0, 0)), vig.filter(ImageFilter.GaussianBlur(80 * k)))

    # badge + titre centres
    big, small = font(int(132 * k)), font(int(30 * k), bold=False)
    d = ImageDraw.Draw(img)
    sub = "propulsé par LiberNT et ReactOS"
    title_w = d.textlength("MadOS", font=big)
    sub_w = d.textlength(sub, font=small)
    badge = mark(int(150 * k), glow=True)
    y0 = int(H * 0.22)
    rgba = img.convert("RGBA")
    rgba.alpha_composite(badge, ((W - badge.width) // 2, y0))
    img = rgba.convert("RGB")
    ty = y0 + badge.height + int(4 * k)
    tx = int((W - title_w) / 2)
    halo = Image.new("RGB", size, (0, 0, 0))
    ImageDraw.Draw(halo).text((tx, ty), "MadOS", font=big, fill=(200, 40, 30))
    img = add(img, halo.filter(ImageFilter.GaussianBlur(22 * k)))
    d = ImageDraw.Draw(img)
    d.text((tx, ty), "Mad", font=big, fill=WHITE)
    d.text((tx + d.textlength("Mad", font=big), ty), "OS", font=big, fill=ACCENT)
    d.text((int((W - sub_w) / 2), ty + int(150 * k)), sub, font=small, fill=MUTED)
    return img


def main():
    make().save(OUT, optimize=True)
    print(f"Fond d'ecran : {OUT.relative_to(TREE)}")


if __name__ == "__main__":
    main()
