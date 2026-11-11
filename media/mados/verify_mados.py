"""
MadOS - verification automatique des fichiers generes par le kit.

Compare chaque fichier a son original LiberNT et controle qu'il respecte le
format attendu par le code qui le charge (uxtheme, inbv, userinit, explorer...).
Code de sortie 0 si tout est bon, 1 sinon.
"""
import colorsys
import io
import re
import struct
import sys

from PIL import Image

from mados_common import TREE, git_original

problems = []


def check(cond, msg):
    print(("  ok    " if cond else "  ECHEC ") + msg)
    if not cond:
        problems.append(msg)


def header(data):
    off, = struct.unpack_from("<I", data, 10)
    dib, = struct.unpack_from("<I", data, 14)
    w, h = struct.unpack_from("<ii", data, 18)
    bpp, = struct.unpack_from("<H", data, 28)
    comp, = struct.unpack_from("<I", data, 30)
    return dict(off=off, dib=dib, w=w, h=h, bpp=bpp, comp=comp)


def bmp_ok(rel, **expect):
    data = (TREE / rel).read_bytes()
    hd = header(data)
    good = data[:2] == b"BM" and all(hd[k] == v for k, v in expect.items())
    check(good, f"{rel} : {hd['w']}x{hd['h']} {hd['bpp']} bits comp={hd['comp']}"
          + ("" if good else f" (attendu {expect})"))
    return data, hd


def theme():
    print("Theme Braise (Win8)")
    base = "media/themes/Win8/win8.msstyles/"
    bmps = sorted((TREE / base / "bitmaps").glob("*.bmp"))
    same_format = changed = 0
    leftover_blue = []
    for p in bmps:
        rel = p.relative_to(TREE).as_posix()
        new, old = p.read_bytes(), git_original(p)
        hn, ho = header(new), header(old)
        if len(new) == len(old) and hn == ho and new[:hn["off"]] == old[:ho["off"]] or hn["bpp"] <= 8 and hn == ho:
            same_format += 1
        changed += new != old
        im = Image.open(io.BytesIO(new)).convert("RGB")
        for n, (r, g, b) in im.getcolors(1 << 20) or []:
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if (r, g, b) != (255, 0, 255) and 0.47 <= h <= 0.72 and s >= 0.35 and v > 0.25:
                leftover_blue.append(rel)
                break
    check(same_format == len(bmps), f"{same_format}/{len(bmps)} bitmaps gardent exactement leur format")
    check(changed > len(bmps) // 2, f"{changed}/{len(bmps)} bitmaps recolorees")
    check(not leftover_blue, f"plus d'accent bleu vif ({len(leftover_blue)} restants{': ' + ', '.join(leftover_blue[:3]) if leftover_blue else ''})")

    for ini in sorted((TREE / base / "textfiles").glob("*.INI")):
        new = ini.read_bytes().decode("utf-16" if ini.read_bytes()[:2] == b"\xff\xfe" else "latin-1").splitlines()
        rawo = git_original(ini)
        old = rawo.decode("utf-16" if rawo[:2] == b"\xff\xfe" else "latin-1").splitlines()
        keys_same = len(new) == len(old) and all(a.split("=")[0] == b.split("=")[0] for a, b in zip(new, old))
        only_colors = all(a == b or re.fullmatch(r"\s*\d{1,3} \d{1,3} \d{1,3}\s*(;.*)?", a.split("=", 1)[1])
                          for a, b in zip(new, old) if "=" in a)
        check(keys_same and only_colors, f"{ini.name} : memes cles, seules des couleurs changent")
        text = "\n".join(new)
        check(re.search(r"(?ms)^\[SysMetrics\][^\[]*?^\s*Highlight\s*=\s*239 68 68\s*$", text) is not None,
              f"{ini.name} : selection rouge braise dans [SysMetrics]")
        logoff = re.search(r"(?ms)^\[StartPanel\.Logoff\][^\[]*?^\s*HotTracking\s*=\s*([\d ]+?)\s*$", text)
        if logoff:
            check(logoff.group(1).strip() == "255 255 255", f"{ini.name} : texte survole du menu Demarrer reste blanc")

    for lang in sorted((TREE / base / "lang").glob("*.rc")):
        t = lang.read_text(encoding="utf-8")
        check('5000, "MadOS"' in t.replace("\t", " "), f"{lang.name} : nom du theme = MadOS")


def boot():
    print("Demarrage")
    rel = "ntos/inbv/resources/"
    pals = []
    for name, (w, h) in {"logo.bmp": (190, 224), "copyright.bmp": (260, 26), "shutdown.bmp": (213, 11)}.items():
        data, hd = bmp_ok(rel + name, w=w, h=h, bpp=4, comp=0)
        pals.append(data[14 + hd["dib"]:14 + hd["dib"] + 64])
    check(len(set(pals)) == 1, "logo, copyright et message d'arret partagent la meme palette VGA")
    pal = pals[0]
    check(pal[0:3] == b"\0\0\0" and pal[60] > 230, "palette VGA : index 0 noir, index 15 blanc")

    data, hd = bmp_ok(rel + "reactos_logo.bmp", bpp=32, comp=3)
    check(hd["w"] > 0 and hd["h"] != 0, "logo UEFI : en-tete accepte par InbvGopValidateWordmarkHeader")
    im = Image.open(io.BytesIO(data))
    check(im.mode == "RGBA" and im.getchannel("A").getextrema() == (0, 255), "logo UEFI : transparence presente")


def ui():
    print("Interface")
    for d in ("base/system/userinit/res/", "dll/cpl/sysdm/resources/"):
        bmp_ok(d + "rosbitmap.bmp", w=320, h=159, bpp=24, comp=0)
        bmp_ok(d + "rosbitmap_mask.bmp", w=320, h=159, bpp=8, comp=0)
    bmp_ok("base/shell/explorer/res/bmp/143.bmp", w=25, h=20, bpp=32, comp=0)
    bmp_ok("dll/win32/shell32/res/bitmaps/reactos.bmp", w=413, h=72, bpp=24, comp=0)
    bmp_ok("dll/win32/shell32/res/bitmaps/line.bmp", w=413, h=5, bpp=24, comp=0)
    ico = Image.open(TREE / "subsystems/win/win32k/user/user32/resources/oic_reactos.ico")
    check({(16, 16), (32, 32), (48, 48)} <= set(ico.info.get("sizes", [])), "icone systeme : 16, 32 et 48 px presents")
    import wave
    with wave.open(str(TREE / "media/sounds/MadOS_Startup.wav")) as w:
        check(w.getnchannels() == 2 and w.getframerate() == 44100 and 2 < w.getnframes() / 44100 < 5,
              "son de demarrage MadOS : WAV stereo 44,1 kHz, 2 a 5 s")
    for rel in ("base/setup/libernt/res/watermark.bmp", "base/setup/welcome/res/title.bmp"):
        o = header(git_original(TREE / rel))
        bmp_ok(rel, w=o["w"], h=o["h"], bpp=24, comp=0)


def shell():
    print("Couleurs ecrites en dur et bouton Demarrer")
    import make_shell
    for rel in make_shell.FILES:
        text = (TREE / rel).read_text(encoding="utf-8", errors="replace")
        left = [m.group(0) for m in make_shell.RGB.finditer(text) if make_shell.is_bluish(*map(int, m.groups()))]
        orig = git_original(TREE / rel).decode("utf-8", errors="replace")
        for old, new in make_shell.EXTRA_TEXT.get(rel, []):       # textes renommes expres
            orig = orig.replace(old, new)
        same_shape = make_shell.RGB.sub("RGB()", text) == make_shell.RGB.sub("RGB()", orig)
        check(not left and same_shape, f"{rel} : plus de bleu, seul le contenu des RGB() change"
              + (f" (restants : {left[:3]})" if left else ""))
    for name in ("default.png", "hover.png", "pressed.png"):
        p = TREE / "media/graphics/start-button" / name
        im = Image.open(p)
        check(im.size == (640, 640) and im.mode == "RGBA", f"bouton Demarrer {name} : 640x640 RGBA")


def names():
    print("Nom MadOS dans les textes affiches")
    import subprocess
    import make_names as mn
    from mados_common import _upstream_ref
    # 1. plus aucun texte affiche "LiberNT" hors attribution
    left = []
    for rel in mn.upstream_files("*.rc"):
        text, _ = mn.decode((TREE / rel).read_bytes())
        text = mn.PROTECTED_BLOCKS.sub("", text)        # blocs d'attribution exclus
        for lit in mn.RC_LITERAL.findall(text):
            if mn.WORD.search(lit) and not mn.KEEP_MARKERS.search(lit):
                left.append(f"{rel}: {lit[:60]}")
    check(not left, f"ressources .rc : plus de texte affiche 'LiberNT' hors attribution ({len(left)} restants)"
          + (f" ex. {left[0]}" if left else ""))
    # 2. les identifiants internes ne bougent pas : dans chaque fichier texte
    #    modifie, le nombre de LiberNT colles a un separateur reste identique
    ident = re.compile(r"[\w\\/.:]LiberNT|LiberNT[\w\\/:]")
    changed = subprocess.run(["git", "-C", str(TREE), "diff", "--name-only", _upstream_ref()],
                             capture_output=True, text=True).stdout.split()
    changed += [l[3:] for l in subprocess.run(["git", "-C", str(TREE), "status", "--porcelain"],
                                              capture_output=True, text=True).stdout.splitlines()]
    bad = []
    for rel in sorted(set(changed)):
        p = TREE / rel
        # les noms de raccourcis .lnk sont renommes expres (controle 3 ci-dessous)
        # README.md est la presentation de MadOS (celle de LiberNT est dans README.LiberNT.md)
        if p.suffix.lower() in (".bmp", ".png", ".jpg", ".md") or not p.is_file() or rel in mn.SHORTCUT_FILES:
            continue
        try:
            before = len(ident.findall(mn.decode(git_original(p))[0]))
        except subprocess.CalledProcessError:
            continue                                  # fichier nouveau
        if len(ident.findall(mn.decode(p.read_bytes())[0])) != before:
            bad.append(rel)
    check(not bad, f"identifiants internes intacts dans {len(set(changed))} fichiers modifies"
          + (f" (differences : {bad[:3]})" if bad else ""))
    # 2c. pas de fins de ligne melangees introduites par le kit
    def mixed(data):
        crlf = data.count(b"\r\n")
        return crlf and data.count(b"\n") != crlf
    mixed_files = []
    for rel in sorted(set(changed)):
        p = TREE / rel
        if p.suffix.lower() not in (".rc", ".inf", ".in", ".c", ".cpp", ".h", ".txt", ".mc") or not p.is_file():
            continue
        try:
            orig = git_original(p)
        except subprocess.CalledProcessError:
            continue
        if mixed(p.read_bytes()) and not mixed(orig):
            mixed_files.append(rel)
    check(not mixed_files, "fins de ligne coherentes dans les fichiers modifies"
          + (f" (melangees : {mixed_files[:3]})" if mixed_files else ""))
    # 2b. la liste des auteurs ("A propos") reste attribuee a LiberNT/ReactOS
    wrong = []
    for p in sorted((TREE / "dll/win32/shell32/lang").glob("*.rc")):
        t, _ = mn.decode(p.read_bytes())
        for m in mn.PROTECTED_BLOCKS.finditer(t):
            if "MadOS" in m.group(0):
                wrong.append(p.name)
    check(not wrong, "liste des auteurs : attribuee a LiberNT dans toutes les langues"
          + (f" (a revoir : {wrong[:4]})" if wrong else ""))
    # 3. raccourcis coherents
    cm = (TREE / "boot/bootdata/CMakeLists.txt").read_text(errors="replace")
    pre = (TREE / "boot/bootdata/preinstall.inf").read_text(errors="replace")
    check('add_livecd_shortcut("Install MadOS"' in cm and '"Install MadOS.lnk"' in pre,
          "raccourci 'Install MadOS' : meme nom a la creation et dans le menu Demarrer")
    hive = (TREE / "boot/bootdata/hivesft.inf").read_text(errors="replace")
    check('"ProductName",2,"MadOS"' in hive, "registre : ProductName = MadOS")


def bootui():
    print("Gestionnaires de demarrage")
    import make_bootui as mb
    from make_shell import is_bluish
    for rel in mb.UIS:
        text = (TREE / rel).read_text(encoding="utf-8", errors="replace")
        left = [m.group(0) for line in text.splitlines()
                if "0x" in line and ("BOOTUI_" in line or "BootUi" in line or "?" in line)
                for m in mb.HEX.finditer(line)
                if is_bluish(int(m.group(1), 16) >> 16, (int(m.group(1), 16) >> 8) & 255, int(m.group(1), 16) & 255)]
        check(text.count('"MadOS"') == 2 and '"LiberNT"' not in text and not left,
              f"{rel} : nom MadOS, plus de couleur bleue" + (f" (restants {left})" if left else ""))
    for rel in mb.LOGOS:
        data = (TREE / rel).read_bytes()
        check(len(data) == 48 * 42 * 4 and data != git_original(TREE / rel), f"{rel} : logo MadOS 48x42 RGBA")


def telemetry():
    print("Donnees de diagnostic")
    hive = (TREE / "boot/bootdata/hivesft.inf").read_text(encoding="utf-8", errors="replace")
    check(re.search(r'"AllowTelemetry",0x[0-9A-Fa-f]+,0x00000000\s*$', hive, re.M) is not None,
          "hivesft.inf : AllowTelemetry = 0 (rien n'est envoye par defaut)")
    langs = sorted((TREE / "dll/cpl/sysdm/lang").glob("*.rc"))
    bad = []
    for p in langs:
        t = p.read_bytes().decode("utf-8", errors="replace")
        block = t[t.find("IDD_ERRORREPORTING"):t.find("IDD_ERRORREPORTING") + 1500]
        if "IDC_SENDREQUIRED" not in block or re.search(r"cannot be turned off|ne peut pas être désactivé", block):
            bad.append(p.name)
    check(not bad, f"panneau Systeme : case d'accord et texte exact dans {len(langs)} langues"
          + (f" (a revoir : {bad[:4]})" if bad else ""))
    cm = (TREE / "base/services/diagdata/CMakeLists.txt").read_text(errors="replace")
    check('set(DIAGDATA_OPTIONAL_DEFAULT "")' in cm, "la compilation ne force plus l'envoi des donnees optionnelles")


def wallpaper():
    print("Fond d'ecran")
    p = TREE / "modules/wallpapers/MadOS.png"
    ok = p.exists() and Image.open(p).format == "PNG"
    check(ok, f"MadOS.png present ({Image.open(p).size if ok else '-'})")
    hive = (TREE / "boot/bootdata/hivedef.inf").read_text(encoding="utf-8", errors="replace")
    check('"Wallpaper",0x00020000,"%SystemRoot%\\Web\\Wallpaper\\MadOS.png"' in hive,
          "hivedef.inf : MadOS.png est le fond d'ecran par defaut")


def welcome():
    print("Bienvenue dans MadOS")
    import configparser
    raw = (TREE / "base/applications/madwelcome/madapps.ini").read_bytes()
    # UTF-16 LE : une conversion de fins de ligne par Git ajoute un octet 0D seul
    # et decale une ligne sur deux (liste d'applications vide a l'ecran)
    check(raw[:2] == b"\xff\xfe" and len(raw) % 2 == 0 and b"\r\n" not in raw.replace(b"\r\x00\n\x00", b""),
          "madapps.ini : UTF-16 intact (fins de ligne non converties par Git)")
    ini = configparser.ConfigParser(interpolation=None)
    try:
        ini.read_string(raw.decode("utf-16"))
        order = [k.strip() for k in ini["Apps"]["Order"].split(",")]
        bad = [k for k in order if not (ini.has_section(k) and ini[k].get("Name") and ini[k].get("Url")
                                        and (ini[k].get("Signer") or ini[k].get("Sha256")))]
    except Exception as e:
        order, bad = [], [str(e)]
    check(order and not bad, f"madapps.ini : {len(order)} applications completes {bad if bad else ''}")


def main():
    theme(); boot(); ui(); shell(); names(); bootui(); telemetry(); wallpaper(); welcome()
    print(f"\n{'Tout est bon.' if not problems else str(len(problems)) + ' probleme(s).'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
