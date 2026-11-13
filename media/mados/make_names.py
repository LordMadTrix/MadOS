"""
MadOS - nom du systeme dans les textes affiches.

Remplace "LiberNT" par "MadOS" la ou l'utilisateur le LIT, et seulement la :
  - chaines des ressources (.rc) et des tables de messages (.mc) ;
  - nom de produit (version.rc, ntverp.h, registre), menu de demarrage (BCD),
    raccourcis (titres et noms de fichiers .lnk, de facon coherente) ;
  - une liste fermee de textes du code C, verifiee une par une.

Ne touche JAMAIS : identifiants, chemins (\\EFI\\LiberNT\\...), cles de registre,
constantes de protocole (KDNET, User-Agent, rapports), tests automatiques.
Garde volontairement l'attribution : copyright, "Project", "Team",
"Contributors", liens libernt.com, mentions "basé sur / based on".
Tout part de l'amont (origin/main-nt10) : relancable a volonte.
"""
import re
import subprocess

from mados_common import TREE, git_original, _upstream_ref

OLD, NEW = "LiberNT", "MadOS"

# Chaine contenant l'un de ces marqueurs : attribution, on n'y touche pas.
KEEP_MARKERS = re.compile(r"copyright|©|\(c\)|project|projet|team|contributors|libernt\.com|based on|basé sur|basee? sur"
                          r"|brought to you", re.I)
# "LiberNT" colle a un separateur de chemin/identifiant : ce n'est pas du texte.
# Un point final de phrase est permis ("... LiberNT."), une extension non ("LiberNT.chm").
WORD = re.compile(r"(?<![\w\\/.:])LiberNT(?![\w\\/:]|\.\w)")

# Dossiers exclus : tests automatiques, theme (gere par make_theme), kit.
EXCLUDE = ("modules/rostests/", "media/themes/Win8/", "media/mados/", "submodules/")

# Textes du code C/C++ (liste fermee) : (fichier, ancien, nouveau, nb attendu)
C_STRINGS = [
    ("bootloader/gui/bmui.c", "startup option for LiberNT", "startup option for MadOS", 1),
    ("bootloader/winload/main.c", '"LiberNT OS Loader"', '"MadOS OS Loader"', 1),
    ("bootloader/winload/install.c", "Installing LiberNT", "Installing MadOS", 1),
    ("bootloader/winload/install.c", "Restoring the previous LiberNT", "Restoring the previous MadOS", 1),
    ("bootloader/winload/install.c", "Checking the LiberNT update", "Checking the MadOS update", 1),
    ("boot/freeldr/freeldr/ntldr/setupldr.c", "Loading LiberNT Setup...", "Loading MadOS Setup...", 1),
    ("dll/shellext/netshell/setup.cpp", 'L"LiberNT Setup"', 'L"MadOS Setup"', 1),
    ("base/applications/winver/winver.c", 'L"LiberNT"', 'L"MadOS"', 2),
    ("sdk/include/psdk/ntverp.h", '"LiberNT Operating System"', '"MadOS Operating System"', 1),
    ("boot/bootdata/hivesft.inf", '"ProductName",2,"LiberNT"', '"ProductName",2,"MadOS"', 1),
    ("bootloader/image/bcd.inf.in", '"Element",,"LiberNT Boot Manager"', '"Element",,"MadOS Boot Manager"', 1),
    ("bootloader/image/bcd.inf.in", '\\Elements\\12000004","Element",,"LiberNT"', '\\Elements\\12000004","Element",,"MadOS"', 1),
]

# Fichiers modifies A LA MAIN dans des commits MadOS : le kit n'y touche jamais
# (il repart de l'amont et effacerait ces modifications). Leurs textes MadOS
# font partie du commit manuel.
#  - bootloader/bootmgr/main.c : menu de demarrage sur demande + "MadOS Boot Manager"
#  - base/services/diagdata, dll/cpl/sysdm/advanced.c|resource.h : telemetrie
#    coupee par defaut (voir make_telemetry.py pour la partie textes)
HAND_MANAGED = ["bootloader/bootmgr/main.c", "bootloader/image/CMakeLists.txt",
                "base/services/diagdata/diagdata.c", "base/services/diagdata/CMakeLists.txt",
                "dll/cpl/sysdm/advanced.c", "dll/cpl/sysdm/resource.h",
                # francais + AZERTY par defaut a l'installation
                "base/setup/libernt/libernt.c", "base/setup/libernt/oobe.c",
                # correctif de compilation Release (NdisDriverObject hors DBG)
                "drivers/network/ndis/ndis/main.c",
                # "Bienvenue dans MadOS" : application, compilation, lancement au 1er demarrage
                "base/applications/madwelcome/madwelcome.c", "base/applications/CMakeLists.txt",
                "boot/bootdata/hivedef.inf",
                # son de demarrage MadOS (fichier genere par make_sounds.py)
                "media/sounds/CMakeLists.txt",
                # detection de mise a jour (MadOS ou LiberNT), icone "A propos",
                # nom du disque "MadOS"
                "base/setup/libernt/upgrade.c", "dll/win32/shell32/wine/shell32_main.c",
                "sdk/cmake/boot_images.cmake",
                # son d'ouverture de session joue des que l'audio est pret
                "base/system/winlogon/sas.c",
                # numero de version MadOS (A propos, panneau Systeme, invite de commandes)
                "sdk/include/reactos/version.cmake", "sdk/include/reactos/buildno.h.cmake",
                "dll/cpl/sysdm/general.c", "base/shell/cmd/wcmdmain.c",
                # pilotes : disque VirtIO (vioblk) a l'installation, Mesa LLVMpipe par defaut
                "drivers/storage/port/CMakeLists.txt", "boot/bootdata/txtsetup.sif",
                "sdk/cmake/config.cmake"]

# Raccourcis : le nom du fichier .lnk doit etre le meme partout ou il est cite.
SHORTCUT_NAMES = {"Install LiberNT": "Install MadOS", "LiberNT Driver Installer": "MadOS Driver Installer"}
SHORTCUT_FILES = ["boot/bootdata/CMakeLists.txt", "boot/bootdata/preinstall.inf", "boot/bootdata/livecd.inf"]

stats = {}


def upstream_files(pattern):
    out = subprocess.run(["git", "-C", str(TREE), "grep", "-l", OLD, _upstream_ref(), "--", pattern],
                         check=True, capture_output=True, text=True).stdout
    files = [line.split(":", 1)[1] for line in out.splitlines()]
    return [f for f in files if not f.startswith(EXCLUDE)]


def rename_text(s):
    """Remplace LiberNT dans un texte affiche, sauf attribution."""
    if KEEP_MARKERS.search(s):
        return s
    return WORD.sub(NEW, s)


def decode(raw):
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16"), "utf-16"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


# Banniere de l'invite de commandes : "LiberNT [Version ...]" puis la ligne de
# copyright (attribution, gardee). Le texte multiligne echappe a RC_LITERAL.
CMD_BANNER = re.compile(r'(WCMD_BANNER,\s*")LiberNT(\s*\[)')

RC_LITERAL = re.compile(r'"(?:[^"\r\n]|"")*"')
# Blocs d'attribution, dans toutes les langues : la liste des auteurs de la
# fenetre "A propos" presente les contributeurs de LiberNT et ReactOS.
PROTECTED_BLOCKS = re.compile(r"^IDD_ABOUT_AUTHORS\s+DIALOGEX.*?^END\b", re.M | re.S)


def rename_outside_protected(text):
    out, pos = [], 0
    for m in PROTECTED_BLOCKS.finditer(text):
        out.append(RC_LITERAL.sub(lambda x: rename_text(x.group(0)), text[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(RC_LITERAL.sub(lambda x: rename_text(x.group(0)), text[pos:]))
    return "".join(out)


def do_rc(rel):
    text, enc = decode(git_original(TREE / rel))
    new = CMD_BANNER.sub(r"\1MadOS\2", rename_outside_protected(text))
    if new != text:
        (TREE / rel).write_bytes(new.encode(enc))
        stats["rc"] = stats.get("rc", 0) + 1


MC_DIRECTIVE = re.compile(r"^\s*(;|MessageId|SymbolicName|Severity|Facility|Language|OutputBase|MessageIdTypedef)", re.I)


def do_mc(rel):
    text, enc = decode(git_original(TREE / rel))
    lines = text.splitlines(keepends=True)
    out = [l if MC_DIRECTIVE.match(l) else rename_text(l) for l in lines]
    new = "".join(out)
    if new != text:
        (TREE / rel).write_bytes(new.encode(enc))
        stats["mc"] = stats.get("mc", 0) + 1


def do_shortcuts_inf():
    rel = "media/inf/shortcuts.inf"
    text, enc = decode(git_original(TREE / rel))
    out = []
    for line in text.splitlines(keepends=True):
        if "=" in line and not line.lstrip().startswith(";"):
            k, v = line.split("=", 1)
            line = k + "=" + rename_text(v)
        out.append(line)
    (TREE / rel).write_bytes("".join(out).encode(enc))


def do_exact(rel, pairs):
    """Remplacements exacts ; chaque motif doit apparaitre le nombre de fois attendu
    (sinon l'amont a change et il faut revoir la liste)."""
    text, enc = decode(git_original(TREE / rel))
    for old, new, expected in pairs:
        n = text.count(old)
        if expected is not None and n != expected:
            raise SystemExit(f"make_names : {rel} contient {n}x {old!r} (attendu {expected}) - revoir la liste")
        text = text.replace(old, new)
    (TREE / rel).write_bytes(text.encode(enc))


def main():
    # Un fichier ne doit etre traite que par une seule passe (chacune repart de
    # l'amont et ecraserait l'autre).
    closed = {rel for rel, *_ in C_STRINGS} | set(SHORTCUT_FILES)
    assert not closed & set(upstream_files("*.rc")) and not closed & set(upstream_files("*.mc"))
    assert not closed & set(HAND_MANAGED), "un fichier modifie a la main est dans la liste du kit"
    for rel in upstream_files("*.rc"):
        do_rc(rel)
    for rel in upstream_files("*.mc"):
        do_mc(rel)
    do_shortcuts_inf()

    by_file = {}
    for rel, old, new, n in C_STRINGS:
        by_file.setdefault(rel, []).append((old, new, n))
    for rel, pairs in by_file.items():
        do_exact(rel, pairs)
    for rel in SHORTCUT_FILES:
        do_exact(rel, [(o, n, None) for o, n in SHORTCUT_NAMES.items()])

    print(f"Noms : {stats.get('rc', 0)} fichiers .rc, {stats.get('mc', 0)} fichiers .mc, "
          f"{len(by_file)} fichiers de code/config (liste fermee), raccourcis renommes.")


if __name__ == "__main__":
    main()
