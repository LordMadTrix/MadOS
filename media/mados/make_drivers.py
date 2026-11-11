"""
MadOS - pilotes ajoutes : declaration des services au demarrage.

  - boot/bootdata/hivesys.inf : service viostor (disque VirtIO de QEMU, KVM,
    Proxmox), demarre au boot comme stornvme, pour pouvoir demarrer MadOS sur
    un disque VirtIO. Doit s'executer APRES make_locale, qui regenere ce
    fichier depuis l'amont.

Le pilote lui-meme est dans drivers/storage/port/viostor (sources VirtIO,
BSD-3-Clause), et son identifiant PCI dans boot/bootdata/txtsetup.sif.
"""
import sys

from mados_common import TREE

HIVESYS = TREE / "boot/bootdata/hivesys.inf"
ANCHOR = "; stornvme driver (StorPort NVMe miniport)"
SERVICE = "viostor"
BLOCK = [
    "; viostor driver (StorPort VirtIO block miniport) - MadOS",
    'HKLM,"SYSTEM\\CurrentControlSet\\Services\\viostor","ErrorControl",0x00010001,0x00000003',
    'HKLM,"SYSTEM\\CurrentControlSet\\Services\\viostor","Group",0x00000000,"SCSI Miniport"',
    'HKLM,"SYSTEM\\CurrentControlSet\\Services\\viostor","ImagePath",0x00020000,"system32\\drivers\\viostor.sys"',
    'HKLM,"SYSTEM\\CurrentControlSet\\Services\\viostor","Start",0x00010001,0x00000000',
    'HKLM,"SYSTEM\\CurrentControlSet\\Services\\viostor","Type",0x00010001,0x00000001',
    "",
]


def main():
    raw = HIVESYS.read_bytes()
    text = raw.decode("utf-8", "surrogateescape")
    if f'Services\\{SERVICE}"' in text:
        raise SystemExit("make_drivers : viostor deja declare (l'etape a-t-elle tourne deux fois sans make_locale ?)")
    if text.count(ANCHOR) != 1:
        raise SystemExit(f"make_drivers : {ANCHOR!r} introuvable dans hivesys.inf - revoir l'ancre")
    eol = "\r\n" if "\r\n" in text else "\n"
    text = text.replace(ANCHOR, eol.join(BLOCK) + ANCHOR)
    HIVESYS.write_bytes(text.encode("utf-8", "surrogateescape"))
    print("Pilotes : service viostor (disque VirtIO) declare au demarrage.")


if __name__ == "__main__":
    sys.exit(main())
