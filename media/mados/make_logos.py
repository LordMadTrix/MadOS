"""
MadOS - logo et toutes ses declinaisons dans LiberNT.

  media/mados/logo/mados_mark.png, mados_logo_light.png, mados_logo_dark.png
  ntos/inbv/resources/reactos_logo.bmp   demarrage UEFI (GOP), 32 bits alpha
  ntos/inbv/resources/logo.bmp           demarrage VGA, 16 couleurs
  ntos/inbv/resources/copyright.bmp      mention en bas de l'ecran VGA
  ntos/inbv/resources/shutdown.bmp       message d'arret (repalette)
  base/system/userinit/res/rosbitmap*.bmp   fenetre du LiveCD
  dll/cpl/sysdm/resources/rosbitmap*.bmp    panneau Systeme
  base/shell/explorer/res/bmp/143.bmp       icone du bouton Demarrer
  base/setup/libernt/res/watermark.bmp      bandeau de l'installateur
  base/setup/welcome/res/title.bmp          titre de l'accueil
"""
from PIL import Image, ImageDraw, ImageFilter

from mados_common import (DESKTOP, KIT, MUTED, STONE_TEXT, TREE, WHITE, color_and_mask, fit_center, font,
                          git_original, lockup_h, mark, save_bmp4, save_bmp24, save_bmp32_alpha_v5,
                          save_bmp32_premul, save_mask8, wordmark)

# Les fenetres du LiveCD et du panneau Systeme suivent le theme : sombre avec
# le theme Braise. Mettre False si elles s'affichent sur fond clair.
DIALOGS_ARE_DARK = True

# Palette VGA 16 couleurs : 0 = noir et 15 = blanc (couleurs du texte de la
# console de demarrage) ; gris aux index 1,3,6,9,12 ; braise ailleurs.
GRAYS = {0: (0, 0, 0), 1: (30, 27, 25), 3: (60, 56, 53), 6: (100, 94, 90),
         9: (150, 144, 140), 12: (200, 196, 193), 15: (246, 245, 244)}
EMBERS = {4: (69, 10, 10), 5: (127, 29, 29), 7: (185, 28, 28), 8: (220, 38, 38),
          2: (239, 68, 68), 10: (249, 115, 22), 11: (251, 146, 60), 13: (254, 215, 170),
          14: (255, 240, 230)}
PALETTE = [{**GRAYS, **EMBERS}[i] for i in range(16)]

R = lambda p: TREE / p


def gray_only(img_rgb):
    """Ramene une image sur les seuls gris de la palette (texte) : chaque
    luminance 0-255 va vers le gris le plus proche (table precalculee)."""
    grays = sorted(GRAYS.values(), key=lambda c: c[0])
    nearest = [min(grays, key=lambda c: abs(c[0] - v)) for v in range(256)]
    lum = img_rgb.convert("L")
    channels = [lum.point([nearest[v][i] for v in range(256)]) for i in range(3)]
    return Image.merge("RGB", channels)


def boot_vga():
    # logo 190x224 : badge + logotype, fond noir
    boot = Image.new("RGBA", (190, 224), (0, 0, 0, 255))
    boot.alpha_composite(mark(150, glow=True), (20, 4))
    wm = wordmark(34, WHITE)
    boot.alpha_composite(wm, ((190 - wm.width) // 2, 224 - wm.height - 12))
    save_bmp4(boot, R("ntos/inbv/resources/logo.bmp"), PALETTE)

    # copyright 260x26, texte gris uniquement
    cp = Image.new("RGB", (260, 26), (0, 0, 0))
    d = ImageDraw.Draw(cp)
    f = font(10, bold=False)
    d.text((0, 0), "MadOS · basé sur LiberNT", font=f, fill=(200, 196, 193))
    d.text((0, 13), "ReactOS © 1996-2026 ReactOS Team & Contributors", font=f, fill=(150, 144, 140))
    save_bmp4(gray_only(cp), R("ntos/inbv/resources/copyright.bmp"), PALETTE)

    # message d'arret : on garde l'image d'origine, ramenee sur les gris
    import io
    orig = Image.open(io.BytesIO(git_original(R("ntos/inbv/resources/shutdown.bmp")))).convert("RGB")
    save_bmp4(gray_only(orig), R("ntos/inbv/resources/shutdown.bmp"), PALETTE)
    return boot


def main():
    out = KIT / "logo"
    out.mkdir(exist_ok=True)
    mark(1024, glow=False).save(out / "mados_mark.png")
    lockup_h(400, STONE_TEXT).save(out / "mados_logo_light.png")
    lockup_h(400, WHITE).save(out / "mados_logo_dark.png")

    # Demarrage UEFI : logotype blanc sur transparent, 652x120
    gop = fit_center(lockup_h(110, WHITE, glow=True), (652, 120))
    save_bmp32_alpha_v5(gop, R("ntos/inbv/resources/reactos_logo.bmp"))

    boot = boot_vga()

    # LiveCD + panneau Systeme : 320x159 + masque alpha
    text_color = WHITE if DIALOGS_ARE_DARK else STONE_TEXT
    bg = (32, 30, 29) if DIALOGS_ARE_DARK else (255, 255, 255)
    rgba = fit_center(fit_center(lockup_h(84, text_color), (288, 130)), (320, 159))
    color, alpha = color_and_mask(rgba, bg)
    for d in ("base/system/userinit/res", "dll/cpl/sysdm/resources"):
        save_bmp24(color, R(d) / "rosbitmap.bmp")
        save_mask8(alpha, R(d) / "rosbitmap_mask.bmp")

    # Bouton Demarrer : 25x20, alpha premultiplie
    start = Image.new("RGBA", (25, 20), (0, 0, 0, 0))
    start.alpha_composite(mark(19, glow=False), (3, 0))
    save_bmp32_premul(start, R("base/shell/explorer/res/bmp/143.bmp"))

    # Bouton Demarrer de la barre des taches (rendu WIC) : 3 PNG 640x640.
    # Le logo d'origine occupe ~65 % du cadre (un peu moins quand il est enfonce).
    from PIL import ImageEnhance
    orb = R("media/graphics/start-button")
    for name, size, light in (("default.png", 416, 1.0), ("hover.png", 416, 1.18), ("pressed.png", 392, 0.82)):
        m = mark(size, glow=False)
        rgb = ImageEnhance.Brightness(m.convert("RGB")).enhance(light).convert("RGBA")
        rgb.putalpha(m.getchannel("A"))
        canvas = Image.new("RGBA", (640, 640), (0, 0, 0, 0))
        canvas.alpha_composite(rgb, ((640 - size) // 2, (640 - size) // 2))
        canvas.save(orb / name, optimize=True)

    # Installateur : bandeau vertical 164x400, fond noir
    wmk = Image.new("RGBA", (164, 400), (0, 0, 0, 255))
    g = Image.new("RGBA", (164, 400), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([-120, 260, 284, 560], fill=(185, 28, 28, 110))
    wmk.alpha_composite(g.filter(ImageFilter.GaussianBlur(40)))
    wmk.alpha_composite(mark(124, glow=True), (20, 96))
    wm = wordmark(26, WHITE)
    wmk.alpha_composite(wm, ((164 - wm.width) // 2, 236))
    save_bmp24(wmk, R("base/setup/libernt/res/watermark.bmp"))

    # Accueil : titre 558x79 sur fond sombre + mention
    W, H = 558, 79
    tt = Image.new("RGBA", (W, H), DESKTOP + (255,))
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([W * 0.55, -H, W * 1.5, H * 1.8], fill=(185, 28, 28, 90))
    tt.alpha_composite(g.filter(ImageFilter.GaussianBlur(30)))
    lk = lockup_h(46, WHITE)
    tt.alpha_composite(lk, ((W - lk.width) // 2, 6))
    ImageDraw.Draw(tt).text((8, H - 14), "© 2026 MadOS · basé sur LiberNT · ReactOS © 1996–2026 ReactOS Team & Contributors",
                            font=font(10, bold=False), fill=MUTED + (255,))
    save_bmp24(tt, R("base/setup/welcome/res/title.bmp"))

    # Apercus
    boot.convert("RGB").save(out / "preview_boot_vga.png")
    prev = Image.new("RGBA", (652, 120), (0, 0, 0, 255)); prev.alpha_composite(gop)
    prev.convert("RGB").save(out / "preview_boot_uefi.png")
    print("Logos MadOS generes.")


if __name__ == "__main__":
    main()
