"""
MadOS - donnees de diagnostic coupees par defaut, activables par l'utilisateur.

Doit s'executer APRES make_names (il modifie les fichiers que make_names vient
de regenerer depuis l'amont) :
  - boot/bootdata/hivesft.inf : AllowTelemetry = 0 par defaut ;
  - dll/cpl/sysdm/lang/*.rc : le dialogue "Donnees de diagnostic" dit la verite
    (rien n'est envoye sans accord ; si l'utilisateur accepte, les donnees vont
    au projet LiberNT) et gagne la case IDC_SENDREQUIRED.

Le code qui va avec (service DiagData, panneau Systeme) est modifie a la main
dans des commits MadOS : base/services/diagdata, dll/cpl/sysdm/advanced.c.
"""
import re

from mados_common import TREE

HIVESFT = TREE / "boot/bootdata/hivesft.inf"
SYSDM_LANG = TREE / "dll/cpl/sysdm/lang"

TEXTS = {
    "fr": ("MadOS n'envoie aucune donnée de diagnostic sans votre accord. Si vous l'activez, la version, "
           "le résultat et la durée du démarrage, le modèle de l'ordinateur, les identifiants des périphériques "
           "et les résumés des plantages sont envoyés au projet LiberNT (libernt.com), sur lequel MadOS est basé.",
           "&Envoyer les données de diagnostic au projet LiberNT"),
    "en": ("MadOS sends no diagnostic data unless you allow it. If you do, the build, the boot result and time, "
           "the hardware model, the device identifiers and crash summaries are sent to the LiberNT project "
           "(libernt.com), which MadOS is based on.",
           "&Send diagnostic data to the LiberNT project"),
}

ALLOW = re.compile(r'^(HKLM,"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\DataCollection",'
                   r'"AllowTelemetry",0x[0-9A-Fa-f]+,)0x[0-9A-Fa-f]+(\s*)$', re.M)


def patch_hivesft():
    raw = HIVESFT.read_bytes()
    text = raw.decode("utf-8", errors="surrogateescape")
    new, n = ALLOW.subn(r"\g<1>0x00000000\g<2>", text)
    if n != 1:
        raise SystemExit(f"make_telemetry : AllowTelemetry trouve {n} fois dans hivesft.inf (attendu 1)")
    HIVESFT.write_bytes(new.encode("utf-8", errors="surrogateescape"))


def patch_dialog(path):
    raw = path.read_bytes()
    enc = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8"
    text = raw.decode(enc, errors="surrogateescape")
    if "IDC_SENDREQUIRED" in text:
        return False                                   # deja applique
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    i_opt = next((i for i, l in enumerate(lines) if "IDC_SENDOPTIONAL" in l), None)
    if i_opt is None:
        raise SystemExit(f"make_telemetry : IDC_SENDOPTIONAL absent de {path.name}")
    i_txt = i_opt - 1
    if not re.search(r"^\s*LTEXT\s+\".*\",\s*IDC_STATIC,\s*7,\s*7,", lines[i_txt]):
        raise SystemExit(f"make_telemetry : structure inattendue du dialogue dans {path.name}")
    i_info = i_opt + 1
    if "IDC_OPTIONALINFO" not in lines[i_info]:
        raise SystemExit(f"make_telemetry : IDC_OPTIONALINFO attendu apres la case dans {path.name}")

    explain, send = TEXTS["fr" if path.name.startswith("fr-") else "en"]
    indent = re.match(r"^\s*", lines[i_txt]).group(0)
    lines[i_txt] = f'{indent}LTEXT "{explain}", IDC_STATIC, 7, 7, 226, 40'
    lines[i_txt + 1:i_txt + 1] = [f'{indent}AUTOCHECKBOX "{send}", IDC_SENDREQUIRED, 7, 50, 226, 10, WS_TABSTOP']
    i_opt += 1
    i_info += 1
    lines[i_opt] = re.sub(r"(IDC_SENDOPTIONAL,\s*7,\s*)46,", r"\g<1>64,", lines[i_opt])
    lines[i_info] = re.sub(r"(IDC_OPTIONALINFO,\s*7,\s*)72,", r"\g<1>88,", lines[i_info])
    path.write_bytes(nl.join(lines).encode(enc, errors="surrogateescape"))
    return True


def main():
    patch_hivesft()
    n = sum(patch_dialog(p) for p in sorted(SYSDM_LANG.glob("*.rc")))
    print(f"Telemetrie : coupee par defaut (AllowTelemetry=0), dialogue mis a jour dans {n} langue(s).")


if __name__ == "__main__":
    main()
