"""
MadOS - couleurs ecrites en dur dans le code de l'interface LiberNT.

Certains elements ne passent pas par le theme : le nouveau menu Demarrer
(startmnu2.cpp) a ses propres palettes, l'ecran de connexion sa couleur
d'accent, etc. On leur applique la meme transformation "Braise" que le theme,
en repartant toujours du code amont (origin/main-nt10) : bleu -> rouge braise,
gris-bleu ardoise -> gris chaud. Seules les couleurs bleutees sont modifiees.
"""
import colorsys
import re

from mados_common import TREE, git_original, make_recolor

recolor = make_recolor(source_hue_deg=206)

# Fichiers retenus (identite visuelle). Volontairement exclus :
#  - user32/windows/paint.c : pinceaux historiques de Windows (DrawFrame...)
#  - setup/libernt/alongside.c : le bleu y represente une partition Windows
FILES = [
    "base/shell/explorer/startmnu2.cpp",       # palettes du menu Demarrer
    "base/shell/explorer/taskswnd.cpp",        # boutons de la barre des taches
    "dll/win32/msgina/logonui.cpp",            # accent de l'ecran de connexion
    "dll/win32/uxtheme/nonclient.c",           # barre de titre sombre
    "dll/win32/shell32/CDefView.cpp",          # jauge d'espace disque
    "dll/win32/shell32/dialogs/drvdefext.cpp", # camembert d'espace disque
    "base/setup/welcome/welcome.c",            # accueil
]

# Textes affiches presents dans ces fichiers (traites ici, et non par
# make_names, pour qu'un fichier ne soit regenere que par une seule etape).
EXTRA_TEXT = {
    "base/setup/welcome/welcome.c": [('TEXT("LiberNT ") TEXT(KERNEL_VERSION_STR)', 'TEXT("MadOS ") TEXT(MADOS_VERSION_FULL_STR)'),
                                     ('TEXT("LiberNT")', 'TEXT("MadOS")')],
}

RGB = re.compile(r"RGB\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)")


def is_bluish(r, g, b):
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return 170 / 360 <= h <= 270 / 360 and s >= 0.10


def patch(rel):
    path = TREE / rel
    text = git_original(path).decode("utf-8", errors="surrogateescape")
    count = 0

    def fix(m):
        nonlocal count
        r, g, b = map(int, m.groups())
        if max(r, g, b) > 255 or not is_bluish(r, g, b):
            return m.group(0)
        count += 1
        return "RGB(%d, %d, %d)" % recolor(r, g, b)

    text = RGB.sub(fix, text)
    # textes affiches dans ces memes fichiers (une seule passe par fichier)
    for old, new in EXTRA_TEXT.get(rel, []):
        if text.count(old) != 1:
            raise SystemExit(f"make_shell : {rel} contient {text.count(old)}x {old!r} (attendu 1)")
        text = text.replace(old, new)
    path.write_bytes(text.encode("utf-8", errors="surrogateescape"))
    return count


def main():
    total = 0
    for rel in FILES:
        n = patch(rel)
        total += n
        print(f"  {n:3d} couleur(s)  {rel}")
    print(f"Interface : {total} couleurs ecrites en dur passees en Braise.")


if __name__ == "__main__":
    main()
