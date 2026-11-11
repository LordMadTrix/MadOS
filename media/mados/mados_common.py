"""
MadOS - module commun du kit d'identite visuelle.

Couleurs, transformation "Braise", dessin du badge et du logotype, et
ecriture des differents formats BMP attendus par LiberNT.
"""
import colorsys
import os
import struct
import subprocess
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

KIT = Path(__file__).resolve().parent
TREE = KIT.parents[1]                      # racine des sources LiberNT
FONTS = TREE / "media" / "fonts"

# ------------------------------------------------------------- palette ----
ACCENT = (239, 68, 68)          # rouge braise
ACCENT_HOT = (248, 113, 113)    # survol
DESKTOP = (28, 25, 23)          # pierre tres sombre
STONE_TEXT = (41, 37, 36)
WHITE = (250, 250, 249)
MUTED = (168, 162, 158)

ACCENT_HUE = colorsys.rgb_to_hsv(*(c / 255 for c in ACCENT))[0]


def font(size, bold=True):
    name = "SourceSansPro-Bold.ttf" if bold else "SourceSansPro-Regular.ttf"
    return ImageFont.truetype(str(FONTS / name), size)


# ------------------------------------------------- transformation Braise ----
def make_recolor(source_hue_deg, blue_range=(170, 270)):
    """Retourne une fonction (r,g,b)->(r,g,b) :
    accent bleu -> rouge braise, gris -> gris chaud ; le reste est conserve.
    Le magenta 255,0,255 (cle de transparence) n'est jamais modifie."""
    src = source_hue_deg / 360
    lo, hi = blue_range[0] / 360, blue_range[1] / 360

    @lru_cache(maxsize=None)        # memes couleurs dans beaucoup de bitmaps
    def recolor(r, g, b):
        if (r, g, b) == (255, 0, 255):
            return r, g, b
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        is_blue = lo <= h <= hi
        # accent = bleu vif (les bleus sombres seulement s'ils sont tres
        # satures) ou bleu pastel clair ; l'ardoise sombre (fonds de panneaux,
        # barres de titre) devient du gris chaud et non du bordeaux.
        vivid = s >= 0.35 and (v >= 0.45 or s >= 0.6)
        if is_blue and (vivid or (s >= 0.18 and v > 0.6)):
            h = (ACCENT_HUE + (h - src) * 0.12) % 1.0
            s = min(1.0, s * 1.1)
            r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
            return round(r2 * 255), round(g2 * 255), round(b2 * 255)
        if s < 0.10 or is_blue:
            lum = round(0.299 * r + 0.587 * g + 0.114 * b) if is_blue else r
            k = 7 * (1 - lum / 255)
            base = lum if is_blue else r
            gg = lum if is_blue else g
            bb = lum if is_blue else b
            return base, max(0, round(gg - k)), max(0, round(bb - 1.6 * k))
        return r, g, b

    return recolor


def recolor_bmp_bytes(data, fn):
    """Recolore un BMP (palette <=8 bits, 24 ou 32 bits) en place, sans
    changer son format. Retourne les octets modifies, ou None si non gere."""
    data = bytearray(data)
    if data[:2] != b"BM":
        return None
    off = struct.unpack_from("<I", data, 10)[0]
    dib = struct.unpack_from("<I", data, 14)[0]
    w, h = struct.unpack_from("<ii", data, 18)
    bpp = struct.unpack_from("<H", data, 28)[0]
    comp = struct.unpack_from("<I", data, 30)[0]
    h = abs(h)
    if bpp <= 8:
        n = struct.unpack_from("<I", data, 46)[0] or (1 << bpp)
        pal = 14 + dib
        for i in range(n):
            p = pal + 4 * i
            r, g, b = fn(data[p + 2], data[p + 1], data[p])
            data[p], data[p + 1], data[p + 2] = b, g, r
        return bytes(data)
    if comp == 3:
        # BI_BITFIELDS : on ne traite que l'ordre standard B,G,R(,A) en memoire
        # les masques suivent toujours les 40 premiers octets de l'en-tete
        masks = struct.unpack_from("<III", data, 54)
        if masks != (0x00FF0000, 0x0000FF00, 0x000000FF):
            return None
    if bpp in (24, 32) and comp in (0, 3):
        step = bpp // 8
        stride = (w * step + 3) & ~3
        for y in range(h):
            row = off + y * stride
            for p in range(row, row + w * step, step):
                r, g, b = fn(data[p + 2], data[p + 1], data[p])
                data[p], data[p + 1], data[p + 2] = b, g, r
        return bytes(data)
    return None


# Reference des fichiers d'origine : la branche LiberNT amont, et non HEAD.
# Une fois les changements MadOS commites, HEAD contient des fichiers deja
# recolores ; repartir de HEAD recolorerait par-dessus a chaque execution.
UPSTREAM = os.environ.get("MADOS_UPSTREAM", "origin/main-nt10")


@lru_cache(maxsize=None)
def _upstream_ref():
    ok = subprocess.run(["git", "-C", str(TREE), "rev-parse", "--verify", "--quiet", UPSTREAM],
                        capture_output=True).returncode == 0
    if not ok:
        print(f"  attention : {UPSTREAM} introuvable, originaux lus depuis HEAD")
    return UPSTREAM if ok else "HEAD"


def git_original(path):
    """Contenu d'origine (LiberNT amont) d'un fichier du depot, sous sa forme
    d'extraction (--filters : fins de ligne CRLF des fichiers marques eol=crlf),
    pour que les fichiers reecrits ne different de l'amont que par leur contenu."""
    rel = Path(path).resolve().relative_to(TREE).as_posix()
    return subprocess.run(["git", "-C", str(TREE), "cat-file", "--filters", f"{_upstream_ref()}:{rel}"],
                          check=True, capture_output=True).stdout


# ----------------------------------------------------------------- badge ----
def mark(size, glow=True):
    """Badge MadOS (RGBA, size x size) : carre arrondi braise, M blanc, braise."""
    S = size * 4
    pad = int(S * 0.08) if glow else 0
    inner = S - 2 * pad

    grad = Image.linear_gradient("L").resize((inner * 2, inner * 2)).rotate(45)
    grad = grad.crop((inner // 2, inner // 2, inner // 2 + inner, inner // 2 + inner))
    grad = ImageOps.colorize(grad, black=(251, 146, 60), mid=(220, 38, 38), white=(110, 18, 18))

    shape = Image.new("L", (inner, inner), 0)
    ImageDraw.Draw(shape).rounded_rectangle([0, 0, inner - 1, inner - 1], radius=int(inner * 0.24), fill=255)

    badge = Image.new("RGBA", (inner, inner), (0, 0, 0, 0))
    badge.paste(grad, (0, 0), shape)

    hl = Image.new("L", (inner, inner), 0)
    ImageDraw.Draw(hl).ellipse([-inner * 0.3, -inner * 0.75, inner * 1.3, inner * 0.42], fill=46)
    hl = ImageChops.multiply(hl.filter(ImageFilter.GaussianBlur(inner * 0.04)), shape)
    badge = Image.composite(Image.new("RGBA", (inner, inner), (255, 255, 255, 255)), badge, hl)

    d = ImageDraw.Draw(badge)
    u = lambda x, y: (x * inner, y * inner)
    pts = [u(0.27, 0.74), u(0.27, 0.33), u(0.50, 0.60), u(0.73, 0.33), u(0.73, 0.74)]
    w = int(inner * 0.115)
    d.line(pts, fill=WHITE + (255,), width=w, joint="curve")
    for p in (pts[0], pts[1], pts[3], pts[4]):
        d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2], fill=WHITE + (255,))

    cx, cy, r = inner * 0.50, inner * 0.27, inner * 0.062
    ember = Image.new("RGBA", (inner, inner), (0, 0, 0, 0))
    ImageDraw.Draw(ember).ellipse([cx - r * 2.4, cy - r * 2.4, cx + r * 2.4, cy + r * 2.4], fill=(254, 215, 170, 150))
    badge = Image.alpha_composite(badge, ember.filter(ImageFilter.GaussianBlur(r * 0.9)))
    ImageDraw.Draw(badge).ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 247, 237, 255))
    badge.putalpha(ImageChops.multiply(badge.getchannel("A"), shape))

    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    if glow:
        halo = Image.new("L", (S, S), 0)
        halo.paste(shape.point(lambda a: a * 0.55), (pad, pad))
        halo = halo.filter(ImageFilter.GaussianBlur(pad * 0.55))
        layer = Image.new("RGBA", (S, S), ACCENT + (0,))
        layer.putalpha(halo)
        canvas = Image.alpha_composite(canvas, layer)
    canvas.alpha_composite(badge, (pad, pad))
    return canvas.resize((size, size), Image.LANCZOS)


def wordmark(height, mad_color):
    """Logotype "MadOS" (RGBA) : "Mad" dans mad_color, "OS" en rouge braise."""
    f = font(int(height * 1.42))
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    w_mad = tmp.textlength("Mad", font=f)
    w_all = tmp.textlength("MadOS", font=f)
    bbox = tmp.textbbox((0, 0), "MadOS", font=f)
    img = Image.new("RGBA", (int(w_all) + 4, bbox[3] + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((0, 0), "Mad", font=f, fill=mad_color + (255,))
    d.text((w_mad, 0), "OS", font=f, fill=ACCENT + (255,))
    return img.crop(img.getbbox())


def lockup_h(height, mad_color, glow=False):
    """Badge + logotype cote a cote."""
    m = mark(height, glow=glow)
    wm = wordmark(int(height * 0.50), mad_color)
    gap = int(height * 0.16)
    img = Image.new("RGBA", (m.width + gap + wm.width, height), (0, 0, 0, 0))
    img.alpha_composite(m, (0, 0))
    img.alpha_composite(wm, (m.width + gap, (height - wm.height) // 2))
    return img


def fit_center(img, size, bg=(0, 0, 0, 0)):
    W, H = size
    s = min(W / img.width, H / img.height, 1.0)
    if s < 1.0:
        img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.LANCZOS)
    out = Image.new("RGBA", size, bg)
    out.alpha_composite(img, ((W - img.width) // 2, (H - img.height) // 2))
    return out


# ------------------------------------------------------------ formats BMP ----
def save_bmp24(img, path):
    img.convert("RGB").save(path, format="BMP")


def save_mask8(alpha, path):
    pal = []
    for i in range(256):
        pal += [i, i, i]
    m = alpha.convert("L").convert("P")
    m.putpalette(pal)
    m.save(path, format="BMP")


def color_and_mask(rgba, bg_rgb=(255, 255, 255)):
    color = Image.new("RGB", rgba.size, bg_rgb)
    color.paste(rgba.convert("RGB"), (0, 0), rgba.getchannel("A").point(lambda a: 255 if a else 0))
    return color, rgba.getchannel("A")


def _bmp(info, extra, rows):
    off = 14 + len(info) + len(extra)
    head = struct.pack("<2sIHHI", b"BM", off + len(rows), 0, 0, off)
    return head + info + extra + rows


def save_bmp32_premul(rgba, path):
    """32 bits BI_RGB, alpha premultiplie (icones d'explorer)."""
    W, H = rgba.size
    px = rgba.load()
    rows = bytearray()
    for y in range(H - 1, -1, -1):
        for x in range(W):
            r, g, b, a = px[x, y]
            rows += bytes((b * a // 255, g * a // 255, r * a // 255, a))
    info = struct.pack("<IiiHHIIiiII", 40, W, H, 1, 32, 0, len(rows), 2835, 2835, 0, 0)
    Path(path).write_bytes(_bmp(info, b"", rows))


def save_bmp32_alpha_v5(rgba, path):
    """32 bits BI_BITFIELDS avec en-tete V5 et alpha non premultiplie
    (logo de demarrage UEFI / GOP de LiberNT)."""
    W, H = rgba.size
    px = rgba.load()
    rows = bytearray()
    for y in range(H - 1, -1, -1):
        for x in range(W):
            r, g, b, a = px[x, y]
            rows += bytes((b, g, r, a))
    info = struct.pack("<IiiHHIIiiII", 124, W, H, 1, 32, 3, len(rows), 2835, 2835, 0, 0)
    info += struct.pack("<IIII", 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    info += struct.pack("<I", 0x73524742)          # 'sRGB'
    info += b"\0" * 36                              # endpoints
    info += struct.pack("<III", 0, 0, 0)            # gamma
    info += struct.pack("<IIII", 4, 0, 0, 0)        # intent, profile data/size, reserved
    assert len(info) == 124
    Path(path).write_bytes(_bmp(info, b"", rows))


def save_bmp4(img_rgb, path, palette16):
    """4 bits non compresse, palette imposee (ecran de demarrage VGA)."""
    assert len(palette16) == 16
    pal_img = Image.new("P", (1, 1))
    flat = []
    for c in palette16:
        flat += list(c)
    # Palette repetee 16 fois : quel que soit l'index choisi par Pillow,
    # (index & 0x0F) designe toujours la bonne couleur.
    pal_img.putpalette(flat * 16)
    q = img_rgb.convert("RGB").quantize(colors=16, palette=pal_img, dither=Image.Dither.FLOYDSTEINBERG)
    W, H = q.size
    stride = ((W + 1) // 2 + 3) & ~3
    px = q.load()
    rows = bytearray()
    for y in range(H - 1, -1, -1):
        row = bytearray(stride)
        for x in range(W):
            v = px[x, y] & 0x0F
            row[x // 2] |= (v << 4) if x % 2 == 0 else v
        rows += row
    pal = b"".join(struct.pack("<BBBB", b, g, r, 0) for (r, g, b) in palette16)
    info = struct.pack("<IiiHHIIiiII", 40, W, H, 1, 4, 0, len(rows), 2835, 2835, 16, 16)
    Path(path).write_bytes(_bmp(info, pal, rows))
