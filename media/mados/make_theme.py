"""
MadOS - theme "Braise" applique au theme par defaut de LiberNT (Win8).

LiberNT charge son theme par defaut sous le nom Themes\\Aero\\aero.msstyles
(registre par defaut, installation, Parametres). Pour que MadOS soit le theme
par defaut partout, on recolore donc directement media/themes/Win8 :
  - bitmaps : accent bleu (0,120,215) -> rouge braise, gris -> gris chaud ;
  - INI : memes couleurs + couleurs systeme forcees (selection, survol, bureau) ;
  - noms affiches : "MadOS Braise".
Chaque execution repart des fichiers d'origine (git HEAD) : relancable a volonte.
"""
import re
from pathlib import Path

from mados_common import BRAISE, TREE, git_original, make_recolor, recolor_bmp_bytes

THEME = TREE / "media" / "themes" / "Win8" / "win8.msstyles"

# Couleurs systeme forcees, uniquement dans [SysMetrics] : les memes cles
# existent ailleurs avec un autre sens (ex. HotTracking = texte survole blanc
# dans [StartPanel.Logoff]).
def overrides(pal):
    return {
        "Highlight": pal.accent,
        "MenuHilight": pal.accent,
        "HotTracking": pal.accent_hot,
        "Background": pal.desktop,
    }
# Une valeur couleur = exactement trois entiers 0-255 separes par des espaces
# (eventuellement suivis d'un commentaire). "3 3 3 3" ou "4, 4, 2" ne sont pas
# des couleurs et ne sont pas touches.
COLOR_VALUE = re.compile(r"^(\s*)(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})(\s*(?:;.*)?)$")


def recolor_ini(path, recolor, over, dst=None):
    raw = git_original(path)
    enc = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "latin-1"
    out, section = [], ""
    for line in raw.decode(enc).splitlines(keepends=True):
        body = line.rstrip("\r\n")
        eol = line[len(body):]
        stripped = body.strip()
        if stripped.startswith("["):
            section = stripped.lower()
        elif "=" in body and not stripped.startswith(";"):
            key, val = body.split("=", 1)
            k = key.strip()
            if section == "[sysmetrics]" and k in over:
                body = f"{key}= {' '.join(map(str, over[k]))}"
            else:
                m = COLOR_VALUE.match(val)
                if m and max(int(m.group(i)) for i in (2, 3, 4)) <= 255:
                    r, g, b = recolor(*(int(m.group(i)) for i in (2, 3, 4)))
                    body = f"{key}={m.group(1)}{r} {g} {b}{m.group(5)}"
        out.append(body + eol)
    (dst or path).write_bytes("".join(out).encode(enc))


# Chaines par identifiant : 1000 = couleur, 2000 = nom complet,
# 5000 = nom du theme, 5007 = description.
NAMES_FR = {1000: "Braise", 2000: "MadOS Braise", 5000: "MadOS",
            5007: "Style visuel MadOS Braise (basé sur le thème de LiberNT)"}
NAMES_EN = {1000: "Ember", 2000: "MadOS Ember", 5000: "MadOS",
            5007: "MadOS Ember visual style (based on the LiberNT theme)"}
STRING_LINE = re.compile(r'^(\s*)(\d+)(\s*,\s*)"[^"\r\n]*"', re.M)


def rename_strings(dst, names_fr, names_en, rc_desc):
    for p in sorted((THEME / "lang").glob("*.rc")):
        names = names_fr if p.name.startswith("fr-") else names_en
        text = git_original(p).decode("utf-8")
        text = STRING_LINE.sub(
            lambda m: f'{m.group(1)}{m.group(2)}{m.group(3)}"{names[int(m.group(2))]}"'
            if int(m.group(2)) in names else m.group(0), text)
        (dst / "lang" / p.name).write_bytes(text.encode("utf-8"))

    rc = THEME / "win8.rc"
    text = git_original(rc).decode("utf-8", errors="surrogateescape")
    text = text.replace('"LiberNT default theme\\0"', f'"{rc_desc}\\0"')
    (dst / "win8.rc").write_bytes(text.encode("utf-8", errors="surrogateescape"))


def build(dst, pal, names_fr, names_en, rc_desc):
    """Recolore le theme Win8 d'origine avec la palette pal dans le dossier
    dst (meme arborescence que win8.msstyles). Retourne (recolorees, total)."""
    recolor = make_recolor(source_hue_deg=206, pal=pal)
    bmps = sorted((THEME / "bitmaps").rglob("*.bmp"))
    done = 0
    for p in bmps:
        data = recolor_bmp_bytes(git_original(p), recolor)
        if data is not None:
            out = dst / p.relative_to(THEME)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            done += 1
    for p in sorted((THEME / "textfiles").glob("*.INI")):
        out = dst / p.relative_to(THEME)
        out.parent.mkdir(parents=True, exist_ok=True)
        recolor_ini(p, recolor, overrides(pal), out)
    (dst / "lang").mkdir(parents=True, exist_ok=True)
    rename_strings(dst, names_fr, names_en, rc_desc)
    return done, len(bmps)


def main():
    done, total = build(THEME, BRAISE, NAMES_FR, NAMES_EN,
                        "MadOS Ember theme (based on LiberNT default theme)")
    print(f"Theme Braise : {done}/{total} bitmaps recolorees, INI et noms mis a jour.")


if __name__ == "__main__":
    main()
