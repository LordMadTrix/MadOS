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
"""
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
    print("Langue : francais (040C) et AZERTY par defaut sur le disque preinstalle et le CD autonome.")


if __name__ == "__main__":
    sys.exit(main())
