"""
MadOS - "Bienvenue dans MadOS" (choix des applications a installer).

Doit s'executer APRES make_names (il modifie shortcuts.inf que make_names
vient de regenerer) :
  - base/applications/madwelcome/madwelcome.ico : icone a partir du badge ;
  - media/inf/shortcuts.inf : raccourci du menu Demarrer (FR + EN).

L'application elle-meme (base/applications/madwelcome) et son lancement au
premier demarrage (RunOnce dans hivedef.inf) sont des fichiers MadOS ecrits
a la main.
"""
import re

from mados_common import TREE, mark

ICON = TREE / "base/applications/madwelcome/madwelcome.ico"
SHORTCUTS = TREE / "media/inf/shortcuts.inf"
LINE = r"%SystemRoot%\system32\madwelcome.exe, %MADWELCOME_TITLE%, %MADWELCOME_DESC%, 0"
STRINGS = {
    "Strings": ("Welcome to MadOS", "Choose and install your applications"),
    "Strings.040C": ("Bienvenue dans MadOS", "Choisir et installer vos applications"),
}


def make_icon():
    m = mark(256, glow=False)
    m.save(ICON, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (256, 256)])


def patch_shortcuts():
    raw = SHORTCUTS.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig", errors="surrogateescape")
    if "madwelcome.exe" in text:
        return
    nl = "\r\n" if "\r\n" in text else "\n"
    # On insere toujours APRES une ligne complete, fin de ligne comprise ("\r\n"
    # ou "\n") : inserer avant le "\n" d'une ligne terminee par "\r\n" melangeait
    # les fins de ligne du fichier.
    # raccourci : juste apres le gestionnaire d'applications
    anchor = re.search(r"^%SystemRoot%\\system32\\rapps\.exe,[^\r\n]*\r?\n", text, re.M)
    if not anchor:
        raise SystemExit("make_welcome : ligne rapps.exe introuvable dans shortcuts.inf")
    text = text[:anchor.end()] + LINE + nl + text[anchor.end():]
    # textes : en tete de [Strings] (anglais, repli) et de [Strings.040C] (francais)
    for section, (title, desc) in STRINGS.items():
        m = re.search(r"^\[" + re.escape(section) + r"\][^\S\r\n]*\r?\n", text, re.M)
        if not m:
            raise SystemExit(f"make_welcome : section [{section}] introuvable dans shortcuts.inf")
        add = f"MADWELCOME_TITLE={title}" + nl + f"MADWELCOME_DESC={desc}" + nl
        text = text[:m.end()] + add + text[m.end():]
    data = text.encode("utf-8", errors="surrogateescape")
    SHORTCUTS.write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)


def main():
    make_icon()
    patch_shortcuts()
    print("Bienvenue dans MadOS : icone et raccourci du menu Demarrer.")


if __name__ == "__main__":
    main()
