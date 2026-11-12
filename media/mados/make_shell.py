"""
MadOS - couleurs ecrites en dur dans le code de l'interface LiberNT.

Certains elements ne passent pas par le theme : le nouveau menu Demarrer
(startmnu2.cpp) a ses propres palettes, l'ecran de connexion sa couleur
d'accent, etc. On leur applique la meme transformation "Braise" que le theme,
en repartant toujours du code amont (origin/main-nt10) : bleu -> rouge braise,
gris-bleu ardoise -> gris chaud. Seules les couleurs bleutees sont modifiees.
"""
import colorsys
import re

from mados_common import TREE, git_original, make_recolor

recolor = make_recolor(source_hue_deg=206)

# Fichiers retenus (identite visuelle). Volontairement exclus :
#  - user32/windows/paint.c : pinceaux historiques de Windows (DrawFrame...)
#  - setup/libernt/alongside.c : le bleu y represente une partition Windows
FILES = [
    "base/shell/explorer/startmnu2.cpp",       # palettes du menu Demarrer
    "base/shell/explorer/taskswnd.cpp",        # boutons de la barre des taches
    "dll/win32/msgina/logonui.cpp",            # accent de l'ecran de connexion
    "dll/win32/uxtheme/nonclient.c",           # barre de titre sombre
    "dll/win32/shell32/CDefView.cpp",          # jauge d'espace disque
    "dll/win32/shell32/dialogs/drvdefext.cpp", # camembert d'espace disque
    "base/setup/welcome/welcome.c",            # accueil
]

# Textes affiches presents dans ces fichiers (traites ici, et non par
# make_names, pour qu'un fichier ne soit regenere que par une seule etape).
# Nouveau menu Demarrer (startmnu2.cpp) : LiberNT y ecrit ses textes en dur en
# anglais. SM2T() les traduit a l'affichage quand l'interface est en francais
# (les chaines anglaises restent les identifiants internes).
SM2T_FR = [
    ("Shut down", "Arr\\u00EAter"), ("Restart", "Red\\u00E9marrer"), ("Log off", "Fermer la session"),
    ("Lock", "Verrouiller"), ("Sleep", "Mettre en veille"), ("Hibernate", "Veille prolong\\u00E9e"),
    ("All Programs", "Tous les programmes"), ("Back", "Pr\\u00E9c\\u00E9dent"),
    ("Documents", "Documents"), ("Pictures", "Images"), ("Music", "Musique"), ("Games", "Jeux"),
    ("Computer", "Ordinateur"), ("Settings", "Param\\u00E8tres"), ("Devices", "P\\u00E9riph\\u00E9riques"),
    ("Network Assistance", "Assistance r\\u00E9seau"), ("Rename", "Renommer"),
    ("Remove from this list", "Retirer de cette liste"),
    ("Search programs and files", "Rechercher programmes et fichiers"),
]
SM2T_FUNC = (
    "#include <powrprof.h>\n\n"
    "/* MadOS : textes du menu Demarrer en francais quand l'interface est en francais. */\n"
    "static LPCWSTR SM2T(LPCWSTR pszEn)\n"
    "{\n"
    "    static const struct { LPCWSTR En; LPCWSTR Fr; } c_Fr[] =\n"
    "    {\n"
    + "".join(f'        {{ L"{en}", L"{fr}" }},\n' for en, fr in SM2T_FR) +
    "    };\n"
    "    if (!pszEn || PRIMARYLANGID(GetUserDefaultUILanguage()) != LANG_FRENCH)\n"
    "        return pszEn;\n"
    "    for (SIZE_T i = 0; i < _countof(c_Fr); i++)\n"
    "        if (!wcscmp(pszEn, c_Fr[i].En))\n"
    "            return c_Fr[i].Fr;\n"
    "    return pszEn;\n"
    "}\n"
)

EXTRA_TEXT = {
    "base/setup/welcome/welcome.c": [('TEXT("LiberNT ") TEXT(KERNEL_VERSION_STR)', 'TEXT("MadOS ") TEXT(MADOS_VERSION_FULL_STR)'),
                                     ('TEXT("LiberNT")', 'TEXT("MadOS")')],
    "base/shell/explorer/startmnu2.cpp": [
        ("#include <powrprof.h>\n", SM2T_FUNC),
        ("::MessageBoxW(hwndOwner, szError, pszAction, MB_OK", "::MessageBoxW(hwndOwner, szError, SM2T(pszAction), MB_OK"),
        ("DrawTextW(hdcMem, c_Items[m_Visible[i]].pszLabel,", "DrawTextW(hdcMem, SM2T(c_Items[m_Visible[i]].pszLabel),"),
        ('row.nType == SM2R_ALLPROGRAMS ? L"All Programs" : L"Back",',
         'row.nType == SM2R_ALLPROGRAMS ? SM2T(L"All Programs") : SM2T(L"Back"),'),
        ("psz = g_SM2RightDefs[j].pszLabel;", "psz = SM2T(g_SM2RightDefs[j].pszLabel);"),
        ('DrawTextW(hdc, L"Shut down", -1, &rcText,', 'DrawTextW(hdc, SM2T(L"Shut down"), -1, &rcText,'),
        ('MessageBoxW(szError, L"Rename", MB_OK', 'MessageBoxW(szError, SM2T(L"Rename"), MB_OK'),
        ('L"Remove from this list");', 'SM2T(L"Remove from this list"));'),
        ('DrawTextW(hdc, L"Search programs and files", -1, &rc,', 'DrawTextW(hdc, SM2T(L"Search programs and files"), -1, &rc,'),
    ],
}

RGB = re.compile(r"RGB\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)")


def is_bluish(r, g, b):
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return 170 / 360 <= h <= 270 / 360 and s >= 0.10


def patch(rel):
    path = TREE / rel
    text = git_original(path).decode("utf-8", errors="surrogateescape")
    count = 0

    def fix(m):
        nonlocal count
        r, g, b = map(int, m.groups())
        if max(r, g, b) > 255 or not is_bluish(r, g, b):
            return m.group(0)
        count += 1
        return "RGB(%d, %d, %d)" % recolor(r, g, b)

    text = RGB.sub(fix, text)
    # textes affiches dans ces memes fichiers (une seule passe par fichier)
    crlf = "\r\n" in text
    for old, new in EXTRA_TEXT.get(rel, []):
        if crlf:        # memes fins de ligne que le fichier
            old, new = old.replace("\n", "\r\n"), new.replace("\n", "\r\n")
        if text.count(old) != 1:
            raise SystemExit(f"make_shell : {rel} contient {text.count(old)}x {old!r} (attendu 1)")
        text = text.replace(old, new)
    path.write_bytes(text.encode("utf-8", errors="surrogateescape"))
    return count


def main():
    total = 0
    for rel in FILES:
        n = patch(rel)
        total += n
        print(f"  {n:3d} couleur(s)  {rel}")
    print(f"Interface : {total} couleurs ecrites en dur passees en Braise.")


if __name__ == "__main__":
    main()
