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
        same_shape = make_shell.RGB.sub("RGB()", text) == make_shell.RGB.sub("RGB()", orig)
        check(not left and same_shape, f"{rel} : plus de bleu, seul le contenu des RGB() change"
              + (f" (restants : {left[:3]})" if left else ""))
    for name in ("default.png", "hover.png", "pressed.png"):
        p = TREE / "media/graphics/start-button" / name
        im = Image.open(p)
        check(im.size == (640, 640) and im.mode == "RGBA", f"bouton Demarrer {name} : 640x640 RGBA")


def wallpaper():
    print("Fond d'ecran")
    p = TREE / "modules/wallpapers/MadOS.png"
    ok = p.exists() and Image.open(p).format == "PNG"
    check(ok, f"MadOS.png present ({Image.open(p).size if ok else '-'})")
    hive = (TREE / "boot/bootdata/hivedef.inf").read_text(encoding="utf-8", errors="replace")
    check('"Wallpaper",0x00020000,"%SystemRoot%\\Web\\Wallpaper\\MadOS.png"' in hive,
          "hivedef.inf : MadOS.png est le fond d'ecran par defaut")


def main():
    theme(); boot(); ui(); shell(); wallpaper()
    print(f"\n{'Tout est bon.' if not problems else str(len(problems)) + ' probleme(s).'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
