"""
MadOS - mode clair "Lumiere" / mode sombre "Braise".

Le theme MadOS (Win8 recolore par make_theme) contient deja les deux modes :
les classes "...Light::" et les images LIGHT_* servent quand le schema de
couleurs est clair (SystemUsesLightTheme = 1). Le panneau qui le choisit
(base/applications/dwmsettings) n'avait ni traduction francaise ni raccourci.

Doit s'executer APRES make_names (qui regenere dwmsettings.rc) et APRES
make_welcome (le raccourci se place apres celui de "Bienvenue dans MadOS") :
  - base/applications/dwmsettings/dwmsettings.rc : inclut lang/fr-FR.rc
    (fichier MadOS) ;
  - media/inf/shortcuts.inf : raccourci "Apparence" dans le menu Demarrer.
"""
import re
import sys

from mados_common import TREE

RC = TREE / "base/applications/dwmsettings/dwmsettings.rc"
SHORTCUTS = TREE / "media/inf/shortcuts.inf"
LINE = r"%SystemRoot%\system32\dwmsettings.exe, %MADAPPEARANCE_TITLE%, %MADAPPEARANCE_DESC%, 0"
STRINGS = {
    "Strings": ("Appearance", "Light or dark mode and window effects"),
    "Strings.040C": ("Apparence", "Mode clair ou sombre et effets des fenetres"),
}


def patch_rc():
    text = RC.read_bytes().decode("utf-8", "surrogateescape")
    m = re.search(r'^#include "lang/en-US\.rc"[^\S\r\n]*\r?\n', text, re.M)
    if not m:
        raise SystemExit("make_appearance : include lang/en-US.rc introuvable dans dwmsettings.rc")
    nl = "\r\n" if m.group(0).endswith("\r\n") else "\n"
    add = "#ifdef LANGUAGE_FR_FR" + nl + '#include "lang/fr-FR.rc"' + nl + "#endif" + nl
    RC.write_bytes((text[:m.end()] + add + text[m.end():]).encode("utf-8", "surrogateescape"))


def patch_shortcuts():
    raw = SHORTCUTS.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig", errors="surrogateescape")
    if "dwmsettings.exe" in text:
        raise SystemExit("make_appearance : raccourci deja present (make_names a-t-il tourne avant ?)")
    nl = "\r\n" if "\r\n" in text else "\n"
    anchor = re.search(r"^%SystemRoot%\\system32\\madwelcome\.exe,[^\r\n]*\r?\n", text, re.M)
    if not anchor:
        raise SystemExit("make_appearance : ligne madwelcome.exe introuvable (make_welcome doit passer avant)")
    text = text[:anchor.end()] + LINE + nl + text[anchor.end():]
    for section, (title, desc) in STRINGS.items():
        m = re.search(r"^\[" + re.escape(section) + r"\][^\S\r\n]*\r?\n", text, re.M)
        if not m:
            raise SystemExit(f"make_appearance : section [{section}] introuvable dans shortcuts.inf")
        add = f"MADAPPEARANCE_TITLE={title}" + nl + f"MADAPPEARANCE_DESC={desc}" + nl
        text = text[:m.end()] + add + text[m.end():]
    SHORTCUTS.write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8", errors="surrogateescape"))


def main():
    patch_rc()
    patch_shortcuts()
    print("Apparence : panneau clair/sombre en francais et raccourci du menu Demarrer.")


if __name__ == "__main__":
    sys.exit(main())
