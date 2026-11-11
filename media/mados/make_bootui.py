"""
MadOS - interface graphique des gestionnaires de demarrage (bootmgr et freeldr).

Les deux bootui.c dessinent eux-memes leur interface : logo (assets/logo.rgba,
48x42 RGBA premultiplie), nom affiche a cote, et couleurs en hexadecimal
(0xRRGGBB). On y applique le badge MadOS, le nom MadOS et la transformation
Braise, en une seule passe par fichier, depuis l'amont.
"""
import re

from mados_common import TREE, git_original, make_recolor, mark
from make_shell import is_bluish

recolor = make_recolor(source_hue_deg=206)

UIS = ["bootloader/gui/bootui.c", "boot/freeldr/freeldr/ui/bootui.c"]
LOGOS = ["bootloader/gui/assets/logo.rgba", "boot/freeldr/freeldr/ui/assets/logo.rgba"]
HEX = re.compile(r"\b0x([0-9A-Fa-f]{6})\b")


def patch_ui(rel):
    text = git_original(TREE / rel).decode("utf-8", errors="surrogateescape")
    n = text.count('"LiberNT"')
    if n != 2:
        raise SystemExit(f"make_bootui : {rel} contient {n}x \"LiberNT\" (attendu 2) - revoir")
    text = text.replace('"LiberNT"', '"MadOS"')
    count = 0

    def fix(m):
        nonlocal count
        v = int(m.group(1), 16)
        r, g, b = v >> 16, (v >> 8) & 255, v & 255
        if not is_bluish(r, g, b):
            return m.group(0)
        count += 1
        r, g, b = recolor(r, g, b)
        return "0x%02X%02X%02X" % (r, g, b)

    # seules les lignes de couleurs : #define BOOTUI_* et appels de dessin
    out = []
    for line in text.splitlines(keepends=True):
        if "0x" in line and ("BOOTUI_" in line or "BootUi" in line or "?" in line):
            line = HEX.sub(fix, line)
        out.append(line)
    (TREE / rel).write_bytes("".join(out).encode("utf-8", errors="surrogateescape"))
    return count


def write_logo(rel):
    """Badge 48x42 (carre de 42 centre), RGBA premultiplie comme l'attend BootUiLogo."""
    from PIL import Image
    canvas = Image.new("RGBA", (48, 42), (0, 0, 0, 0))
    canvas.alpha_composite(mark(42, glow=False), (3, 0))
    out = bytearray()
    for r, g, b, a in canvas.getdata():
        out += bytes((r * a // 255, g * a // 255, b * a // 255, a))
    assert len(out) == 48 * 42 * 4
    (TREE / rel).write_bytes(bytes(out))


def main():
    for rel in UIS:
        n = patch_ui(rel)
        print(f"  {n:3d} couleur(s) + nom  {rel}")
    for rel in LOGOS:
        write_logo(rel)
    print("Gestionnaires de demarrage : nom, couleurs et logo MadOS.")


if __name__ == "__main__":
    main()
