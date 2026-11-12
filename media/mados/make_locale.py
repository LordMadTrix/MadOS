"""
MadOS - francais et clavier AZERTY des le premier ecran.

Le disque preinstalle (VHD) et le CD autonome demarrent sur le bureau avant
l'assistant d'installation : sans ce reglage, ce bureau (dossiers, menus,
"Bienvenue dans MadOS") est en anglais. L'assistant garde le choix de la
langue (francais propose par defaut, voir base/setup/libernt).

  - boot/bootdata/hivesys.inf : langue du systeme (Default, InstallLanguage)
    -> 040C, regenere depuis l'amont ;
  - boot/bootdata/preinstall.inf, livecd.inf : clavier et paramètres
    regionaux de l'utilisateur -> 0000040C. Doit s'executer APRES make_names,
    qui regenere ces deux fichiers (noms de raccourcis).
  - raccourcis du menu Demarrer et du bureau crees a la compilation : noms
    francais (boot/bootdata/CMakeLists.txt, la liste "RecentlyAdded" de
    preinstall.inf/livecd.inf, subsystems/linux/lxterm/CMakeLists.txt). Les
    dossiers (Accessories, System Tools...) gardent leur nom : le menu
    Demarrer ouvre "Games" par son nom ;
  - media/inf/shortcuts.inf : "Applications Manager" non traduit dans
    [Strings.040C].
"""
import re
import sys

from mados_common import TREE, git_original

FR = "040C"

HIVESYS = "boot/bootdata/hivesys.inf"
HIVESYS_PAIRS = [
    ('Nls\\Language","Default",0x00000000,"0409"', f'Nls\\Language","Default",0x00000000,"{FR}"'),
    ('Nls\\Language","InstallLanguage",0x00000000,"0409"', f'Nls\\Language","InstallLanguage",0x00000000,"{FR}"'),
]
USER_PAIRS = [
    ('HKCU,"Keyboard Layout\\Preload","1",0x00000000,"00000409"',
     f'HKCU,"Keyboard Layout\\Preload","1",0x00000000,"0000{FR}"'),
    ('HKCU,"Control Panel\\International","Locale",0x00000000,"00000409"',
     f'HKCU,"Control Panel\\International","Locale",0x00000000,"0000{FR}"'),
]
# fichier -> paires attendues (le CD autonome ne fixe que le clavier)
USER_FILES = {"boot/bootdata/preinstall.inf": USER_PAIRS, "boot/bootdata/livecd.inf": USER_PAIRS[:1]}


# Noms des raccourcis crees a la compilation (anglais -> francais).
# SANS ACCENTS : mkisofs (ISO d'installation) refuse les noms non ASCII. On
# reformule plutot que d'ecrire un mot faux ("taches" sans accent...).
SHORTCUTS_FR = {
    "Install MadOS": "Installer MadOS",
    "Read Me": "Lisez-moi",
    "LiberNT Explorer": "Explorateur de fichiers",
    "Linux Terminal": "Terminal Linux",
    "Command Prompt": "Invite de commandes",
    "Applications Manager": "Gestionnaire d'applications",
    "Device Manager": "Gestionnaire d'appareils",
    "Disk Management": "Gestion des disques",
    "Event Viewer": "Visionneuse de journaux",
    "Service Manager": "Gestionnaire de services",
    "System Configuration": "Configuration (MSConfig)",
    "Magnify": "Loupe",
    "On-Screen Keyboard": "Clavier visuel",
    "Remote Desktop Connection": "Bureau distant",
    "Multimedia Player": "Lecteur de films et musique",
    "Sound Recorder": "Enregistreur de sons",
    "Character Map": "Table de symboles",
    "Clipboard Viewer": "Visionneuse du Presse-papiers",
    "Keyboard Layout Switcher": "Changement de clavier",
    "ReactX Diagnostic": "Diagnostic ReactX",
    "Registry Editor": "Base de registre",
    "Task Manager 11": "Programmes en cours (nouveau)",
    "Task Manager": "Programmes en cours",
    "MadOS Driver Installer": "Installateur de pilotes MadOS",
    "Optional Components": "Composants optionnels",
    "Calculator": "Calculatrice",
    "Notepad": "Bloc-notes",
    "Spider Solitaire": "Solitaire Spider",
}
SHORTCUT_FILES = ["boot/bootdata/CMakeLists.txt", "boot/bootdata/preinstall.inf", "boot/bootdata/livecd.inf"]
LXTERM = "subsystems/linux/lxterm/CMakeLists.txt"          # regenere depuis l'amont
SHORTCUTS_INF = TREE / "media/inf/shortcuts.inf"


def shortcut_patterns():
    # Les noms les plus longs d'abord ; seulement "Nom" entre guillemets ou un
    # fichier Nom.lnk precede de ", \ ou / (jamais notepad.exe, ni "Spider
    # Solitaire.lnk" pris pour "Solitaire.lnk").
    for en in sorted(SHORTCUTS_FR, key=len, reverse=True):
        fr = SHORTCUTS_FR[en]
        yield en, re.compile(r'(?<=["\\/])' + re.escape(en) + r'(?=\.lnk|")'), fr


def rename_shortcuts(texts):
    """texts : {rel: texte} ; renvoie les textes modifies. Chaque nom doit etre trouve."""
    for en, pattern, fr in shortcut_patterns():
        found = 0
        for rel in texts:
            texts[rel], n = pattern.subn(fr, texts[rel])
            found += n
        if not found:
            raise SystemExit(f"make_locale : raccourci {en!r} introuvable - revoir SHORTCUTS_FR")
    return texts


def fix_rapps_title_fr():
    raw = SHORTCUTS_INF.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig", "surrogateescape")
    m = re.search(r"^\[Strings\.040C\][^\[]*", text, re.M)
    if not m or m.group(0).count("RAPPS_TITLE_SHORT=Applications Manager") != 1:
        raise SystemExit("make_locale : RAPPS_TITLE_SHORT anglais introuvable dans [Strings.040C]")
    sec = m.group(0).replace("RAPPS_TITLE_SHORT=Applications Manager", "RAPPS_TITLE_SHORT=Gestionnaire d'applications")
    text = text[:m.start()] + sec + text[m.end():]
    SHORTCUTS_INF.write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8", "surrogateescape"))


# Programmes sans traduction francaise : on inclut un lang/fr-FR.rc (fichier
# MadOS) apres l'anglais. Leurs .rc sont regeneres par make_names.
FR_RC = {
    "base/applications/winver/winver.rc":
        ('#ifdef LANGUAGE_EN_US\n    #include "lang/en-US.rc"\n#endif\n',
         '#ifdef LANGUAGE_FR_FR\n    #include "lang/fr-FR.rc"\n#endif\n'),
}


def add_fr_rc():
    for rel, (anchor, add) in FR_RC.items():
        p = TREE / rel
        text = p.read_bytes().decode("utf-8", "surrogateescape")
        if "\r\n" in text:
            anchor, add = anchor.replace("\n", "\r\n"), add.replace("\n", "\r\n")
        if text.count(anchor) != 1:
            raise SystemExit(f"make_locale : bloc anglais introuvable dans {rel}")
        p.write_bytes(text.replace(anchor, anchor + add).encode("utf-8", "surrogateescape"))


def replace_exact(rel, text, pairs):
    for old, new in pairs:
        if text.count(old) != 1:
            raise SystemExit(f"make_locale : {rel} contient {text.count(old)}x {old!r} (attendu 1)")
        text = text.replace(old, new)
    return text


def main():
    raw = git_original(TREE / HIVESYS)
    (TREE / HIVESYS).write_bytes(replace_exact(HIVESYS, raw.decode("utf-8", "surrogateescape"),
                                               HIVESYS_PAIRS).encode("utf-8", "surrogateescape"))
    for rel, pairs in USER_FILES.items():
        p = TREE / rel
        text = p.read_bytes().decode("utf-8", "surrogateescape")
        p.write_bytes(replace_exact(rel, text, pairs).encode("utf-8", "surrogateescape"))
    texts = {rel: (TREE / rel).read_bytes().decode("utf-8", "surrogateescape") for rel in SHORTCUT_FILES}
    texts[LXTERM] = git_original(TREE / LXTERM).decode("utf-8", "surrogateescape")
    for rel, text in rename_shortcuts(texts).items():
        (TREE / rel).write_bytes(text.encode("utf-8", "surrogateescape"))
    fix_rapps_title_fr()
    add_fr_rc()
    print("Langue : francais (040C) et AZERTY par defaut sur le disque preinstalle et le CD autonome ; "
          f"{len(SHORTCUTS_FR)} raccourcis en francais.")


if __name__ == "__main__":
    sys.exit(main())
