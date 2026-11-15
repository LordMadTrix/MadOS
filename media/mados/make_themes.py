"""
MadOS - themes supplementaires : Ocean, Foret, Amethyste et Ambre.

Chaque theme reprend les dessins de Braise avec ses propres couleurs :
  - media/themes/<Nom>/<Nom>.msstyles/ : style visuel (theme Win8 d'origine
    recolore, modes sombre et clair) ;
  - media/themes/<Nom>/StartButton/*.png : bouton Demarrer ;
  - media/themes/<Nom>/Icons/*.ico : icones du bureau (Poste de travail,
    Mes documents, Reseau, Corbeille) ;
  - modules/wallpapers/MadOS-<Nom>.png : fond d'ecran ;
  - media/themes/CMakeLists.txt : un add_subdirectory par theme ;
  - media/inf/shortcuts.inf : raccourci "Themes" (application madthemes) ;
  - base/applications/madthemes/madthemes.ico : icone de l'application.
Tout est installe dans %SystemRoot%\\Resources\\Themes\\<Nom>\\. L'application
"Themes" (base/applications/madthemes, ecrite a la main) applique un theme
d'un clic ; Explorer prend le bouton Demarrer du theme actif.

Doit s'executer APRES make_appearance (le raccourci se place apres
"Apparence" dans shortcuts.inf).
"""
import colorsys
import re
import shutil
import subprocess
from functools import lru_cache

from PIL import Image, ImageDraw, ImageEnhance

from mados_common import BRAISE, TREE, Palette, _upstream_ref, git_original, mark
import make_theme
import make_wallpaper

THEMES_DIR = TREE / "media" / "themes"
WIN8 = THEMES_DIR / "Win8" / "win8.msstyles"
SHORTCUTS = TREE / "media" / "inf" / "shortcuts.inf"
APP_ICON = TREE / "base" / "applications" / "madthemes" / "madthemes.ico"
LINE = r"%SystemRoot%\system32\madthemes.exe, %MADTHEMES_TITLE%, %MADTHEMES_DESC%, 0"
STRINGS = {
    "Strings": ("Themes", "Colors, wallpaper and icons"),
    "Strings.040C": ("Thèmes", "Couleurs, fond d'écran et icônes"),
}

THEMES = [
    (Palette("Ocean", (59, 130, 246), (96, 165, 250), (15, 23, 42),
             badge=((56, 189, 248), (37, 99, 235), (23, 37, 84)),
             ember=((186, 230, 253, 150), (240, 249, 255)),
             glow=(10, 60, 150),
             ribbons=[(59, 130, 246), (14, 165, 233), (30, 64, 175), (56, 189, 248)],
             sparks=(70, 170, 255), halo=(30, 80, 200), grey_tint=(1.6, 0.6, 0)),
     "Océan", "Ocean"),
    (Palette("Foret", (16, 185, 129), (52, 211, 153), (17, 26, 22),
             badge=((132, 204, 22), (5, 150, 105), (6, 60, 45)),
             ember=((209, 250, 229, 150), (236, 253, 245)),
             glow=(10, 110, 50),
             ribbons=[(16, 185, 129), (132, 204, 22), (4, 120, 87), (52, 211, 153)],
             sparks=(90, 230, 140), halo=(20, 150, 80), grey_tint=(1.2, 0, 1.2)),
     "Forêt", "Forest"),
    (Palette("Amethyste", (168, 85, 247), (192, 132, 252), (24, 20, 32),
             badge=((232, 121, 249), (147, 51, 234), (59, 7, 100)),
             ember=((243, 232, 255, 150), (250, 245, 255)),
             glow=(100, 30, 150),
             ribbons=[(168, 85, 247), (217, 70, 239), (107, 33, 168), (192, 132, 252)],
             sparks=(200, 120, 255), halo=(130, 40, 200), grey_tint=(0.4, 1.6, 0)),
     "Améthyste", "Amethyst"),
    (Palette("Ambre", (245, 158, 11), (251, 191, 36), (28, 25, 23),
             badge=((253, 224, 71), (245, 158, 11), (120, 53, 15)),
             ember=((254, 243, 199, 150), (255, 251, 235)),
             glow=(150, 80, 10),
             ribbons=[(245, 158, 11), (251, 191, 36), (180, 83, 9), (253, 186, 116)],
             sparks=(255, 190, 80), halo=(200, 120, 20), grey_tint=(0, 1, 1.6)),
     "Ambre", "Amber"),
]

# Icones du bureau : nom installe -> icone d'origine de shell32
ICONS = {
    "computer": "16",
    "network": "18",
    "documents": "235",
    "trash-empty": "32",
    "trash-full": "33",
}
ICON_SRC = TREE / "dll" / "win32" / "shell32" / "res" / "icons"

THEME_CMAKE = """# MadOS - theme {name} (genere par media/mados/make_themes.py)
add_subdirectory({key}.msstyles)

file(GLOB _start CONFIGURE_DEPENDS "${{CMAKE_CURRENT_SOURCE_DIR}}/StartButton/*.png")
foreach(_f ${{_start}})
    add_cd_file(FILE "${{_f}}" DESTINATION reactos/Resources/Themes/{key}/StartButton FOR all)
endforeach()
file(GLOB _icons CONFIGURE_DEPENDS "${{CMAKE_CURRENT_SOURCE_DIR}}/Icons/*.ico")
foreach(_f ${{_icons}})
    add_cd_file(FILE "${{_f}}" DESTINATION reactos/Resources/Themes/{key}/Icons FOR all)
endforeach()
"""


def upstream_files(prefix):
    out = subprocess.run(["git", "-C", str(TREE), "ls-tree", "-r", "--name-only", _upstream_ref(), prefix],
                         check=True, capture_output=True, text=True).stdout
    return [TREE / l for l in out.splitlines() if l]


def build_msstyles(pal, fr, en):
    dst = THEMES_DIR / pal.key / f"{pal.key}.msstyles"
    if dst.exists():
        shutil.rmtree(dst)
    # 1. copie de tout le theme d'origine (sources, textes, langues...)
    for src in upstream_files(WIN8.relative_to(TREE).as_posix() + "/"):
        rel = src.relative_to(WIN8)
        if rel.as_posix() == "CMakeLists.txt":
            continue
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(git_original(src))
    # 2. couleurs et noms
    names_fr = {1000: fr, 2000: f"MadOS {fr}", 5000: f"MadOS {fr}",
                5007: f"Style visuel MadOS {fr} (basé sur le thème de LiberNT)"}
    names_en = {1000: en, 2000: f"MadOS {en}", 5000: f"MadOS {en}",
                5007: f"MadOS {en} visual style (based on the LiberNT theme)"}
    done, total = make_theme.build(dst, pal, names_fr, names_en,
                                   f"MadOS {en} theme (based on LiberNT default theme)")
    # 3. CMakeLists : cible et dossier d'installation propres au theme
    cm = git_original(WIN8 / "CMakeLists.txt").decode("utf-8")
    target = f"{pal.key.lower()}.msstyles"      # avec extension, comme win8.msstyles
    cm = cm.replace("win8.msstyles", target)
    cm = cm.replace(f"DESTINATION reactos/Resources/Themes/Aero NAME_ON_CD aero.msstyles",
                    f"DESTINATION reactos/Resources/Themes/{pal.key} NAME_ON_CD {pal.key}.msstyles")
    if f"Themes/{pal.key} NAME_ON_CD" not in cm or "win8.msstyles" in cm:
        raise SystemExit("make_themes : CMakeLists de win8.msstyles inattendu")
    (dst / "CMakeLists.txt").write_text(cm, encoding="utf-8")
    (THEMES_DIR / pal.key / "CMakeLists.txt").write_text(
        THEME_CMAKE.format(name=fr.encode("ascii", "replace").decode(), key=pal.key), encoding="utf-8")
    return done, total


def build_start_button(pal):
    """Meme dessin que le bouton Demarrer de Braise (make_logos), aux couleurs du theme."""
    out = THEMES_DIR / pal.key / "StartButton"
    out.mkdir(parents=True, exist_ok=True)
    for name, size, light in (("default.png", 416, 1.0), ("hover.png", 416, 1.18), ("pressed.png", 392, 0.82)):
        m = mark(size, glow=False, pal=pal)
        rgb = ImageEnhance.Brightness(m.convert("RGB")).enhance(light).convert("RGBA")
        rgb.putalpha(m.getchannel("A"))
        canvas = Image.new("RGBA", (640, 640), (0, 0, 0, 0))
        canvas.alpha_composite(rgb, ((640 - size) // 2, (640 - size) // 2))
        canvas.save(out / name, optimize=True)


def icon_recolor(pal, src_hue):
    tr, tg, tb = pal.grey_tint

    @lru_cache(maxsize=None)
    def fn(r, g, b):
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s >= 0.15:
            d = ((h - src_hue + 0.5) % 1.0) - 0.5
            r2, g2, b2 = colorsys.hsv_to_rgb((pal.hue + d * 0.25) % 1.0, s, v)
            return round(r2 * 255), round(g2 * 255), round(b2 * 255)
        k = 7 * (1 - r / 255)
        return (max(0, round(r - tr * k)), max(0, round(g - tg * k)), max(0, round(b - tb * k)))

    return fn


def dominant_hue(img):
    """Teinte moyenne (circulaire) des pixels colores et opaques."""
    import math
    x = y = 0.0
    for r, g, b, a in img.getdata():
        if a < 128:
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s >= 0.15:
            x += math.cos(h * math.tau) * s
            y += math.sin(h * math.tau) * s
    return (math.atan2(y, x) / math.tau) % 1.0 if (x or y) else 0.0


def build_icons(pal):
    out = THEMES_DIR / pal.key / "Icons"
    out.mkdir(parents=True, exist_ok=True)
    for name, num in ICONS.items():
        ico = Image.open(ICON_SRC / f"{num}.ico")
        sizes = sorted(ico.ico.sizes())
        frames = [ico.ico.getimage(sz).convert("RGBA") for sz in sizes]
        fn = icon_recolor(pal, dominant_hue(frames[-1]))
        done = []
        for fr in frames:
            px = [fn(r, g, b) + (a,) for r, g, b, a in fr.getdata()]
            im = Image.new("RGBA", fr.size)
            im.putdata(px)
            done.append(im)
        done[-1].save(out / f"{name}.ico", format="ICO", sizes=sizes, append_images=done[:-1])


def build_app_icon():
    """Icone de "Themes" : quatre carres arrondis aux couleurs des themes."""
    S = 256
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cols = [BRAISE.accent] + [pal.accent for pal, _, _ in THEMES[:3]]
    pad, gap = 16, 16
    c = (S - 2 * pad - gap) // 2
    for i, col in enumerate(cols):
        x = pad + (i % 2) * (c + gap)
        y = pad + (i // 2) * (c + gap)
        d.rounded_rectangle([x, y, x + c - 1, y + c - 1], radius=c // 4, fill=col + (255,))
    APP_ICON.parent.mkdir(parents=True, exist_ok=True)
    img.save(APP_ICON, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (256, 256)])


def patch_themes_cmake():
    p = THEMES_DIR / "CMakeLists.txt"
    text = git_original(p).decode("utf-8")
    nl = "\r\n" if "\r\n" in text else "\n"
    if not text.endswith(nl):
        text += nl
    for pal, _, _ in THEMES:
        text += f"add_subdirectory({pal.key})" + nl
    p.write_bytes(text.encode("utf-8"))


def patch_shortcuts():
    raw = SHORTCUTS.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig", errors="surrogateescape")
    if "madthemes.exe" in text:
        raise SystemExit("make_themes : raccourci deja present (make_names a-t-il tourne avant ?)")
    nl = "\r\n" if "\r\n" in text else "\n"
    anchor = re.search(r"^%SystemRoot%\\system32\\dwmsettings\.exe,[^\r\n]*\r?\n", text, re.M)
    if not anchor:
        raise SystemExit("make_themes : ligne dwmsettings.exe introuvable (make_appearance doit passer avant)")
    text = text[:anchor.end()] + LINE + nl + text[anchor.end():]
    for section, (title, desc) in STRINGS.items():
        m = re.search(r"^\[" + re.escape(section) + r"\][^\S\r\n]*\r?\n", text, re.M)
        if not m:
            raise SystemExit(f"make_themes : section [{section}] introuvable dans shortcuts.inf")
        add = f"MADTHEMES_TITLE={title}" + nl + f"MADTHEMES_DESC={desc}" + nl
        text = text[:m.end()] + add + text[m.end():]
    SHORTCUTS.write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8", errors="surrogateescape"))


def main():
    for pal, fr, en in THEMES:
        done, total = build_msstyles(pal, fr, en)
        build_start_button(pal)
        build_icons(pal)
        make_wallpaper.make(pal=pal).save(TREE / "modules" / "wallpapers" / f"MadOS-{pal.key}.png", optimize=True)
        print(f"Theme {pal.key} : {done}/{total} bitmaps, fond d'ecran, bouton Demarrer, icones.")
    build_app_icon()
    patch_themes_cmake()
    patch_shortcuts()


if __name__ == "__main__":
    main()
