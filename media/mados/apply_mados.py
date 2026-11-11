"""
MadOS - applique toute l'identite visuelle a l'arbre LiberNT.

    python3 media/mados/apply_mados.py

1. theme Braise (recoloration du theme par defaut Win8 / aero.msstyles)
2. fond d'ecran MadOS.png + reglage par defaut du registre
3. logos (demarrage UEFI et VGA, LiveCD, Systeme, Demarrer, installateur)
4. marque les fichiers .rc concernes comme modifies, pour que ninja
   recompile les ressources (il ne suit pas toujours les images incluses).
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mados_common import TREE  # noqa: E402
import make_bootui  # noqa: E402
import make_logos  # noqa: E402
import make_names  # noqa: E402
import make_shell  # noqa: E402
import make_telemetry  # noqa: E402
import make_theme  # noqa: E402
import make_wallpaper  # noqa: E402
import verify_mados  # noqa: E402

RC_TO_TOUCH = [
    "media/themes/Win8/win8.msstyles/win8.rc",
    "ntos/inbv/bootanim.rc",
    "base/system/userinit/userinit.rc",
    "dll/cpl/sysdm/sysdm.rc",
    "base/shell/explorer/explorer.rc",
    "base/setup/libernt/libernt.rc",
    "base/setup/welcome/welcome.rc",
]


def set_default_wallpaper():
    p = TREE / "boot" / "bootdata" / "hivedef.inf"
    text = p.read_text(encoding="utf-8", errors="surrogateescape")
    new = re.sub(r'(HKCU,"Control Panel\\Desktop","Wallpaper",0x00020000,")[^"]*(")',
                 r'\1%SystemRoot%\\Web\\Wallpaper\\MadOS.png\2', text)
    if new != text:
        p.write_text(new, encoding="utf-8", errors="surrogateescape")
    print("Fond d'ecran par defaut : MadOS.png")


def touch_rc():
    now = time.time()
    for rel in RC_TO_TOUCH:
        p = TREE / rel
        if p.exists():
            os.utime(p, (now, now))
        else:
            print(f"  (absent) {rel}")


def report_divergence():
    """Signale les fichiers que le kit a fait diverger du dernier commit.
    Sur une branche a jour, la liste doit etre vide ; sinon, soit le kit a
    change (normal, a commiter), soit le fichier contenait des modifications
    manuelles que le kit vient d'ecraser (a restaurer, et a declarer dans
    make_names.HAND_MANAGED)."""
    import subprocess
    out = subprocess.run(["git", "-C", str(TREE), "status", "--porcelain", "--untracked-files=no"],
                         capture_output=True, text=True).stdout.splitlines()
    changed = [l[3:] for l in out if not l[3:].startswith("media/mados/")]
    if changed:
        print(f"\nAttention : {len(changed)} fichier(s) different(s) du dernier commit apres le kit :")
        for rel in changed[:10]:
            print(f"  {rel}")
        print("  -> kit modifie (a commiter) ou modifications manuelles ecrasees (git checkout -- <fichier>).")


def main():
    make_theme.main()
    make_wallpaper.main()
    set_default_wallpaper()
    make_logos.main()
    make_shell.main()
    make_names.main()
    make_telemetry.main()        # apres make_names : modifie ses fichiers
    make_bootui.main()
    touch_rc()
    print("\nVerification :")
    if verify_mados.main() != 0:
        sys.exit(1)
    report_divergence()
    print("MadOS applique. Recompiler : cd output-Clang-amd64-debug && ninja liberntvhd")


if __name__ == "__main__":
    main()
