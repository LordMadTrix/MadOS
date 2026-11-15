/*
 * PROJECT:     MadOS
 * LICENSE:     GPL-3.0-or-later (https://spdx.org/licenses/GPL-3.0-or-later)
 * PURPOSE:     "Themes" - apply a MadOS theme in one click
 *
 * A MadOS theme is a visual style (Resources\Themes\<Dir>\<File>), a
 * wallpaper (Web\Wallpaper), a Start button (<Dir>\StartButton, read by
 * Explorer) and desktop icons (<Dir>\Icons, set per user in
 * HKCU\...\Explorer\CLSID\{...}\DefaultIcon). Braise is the default theme
 * and keeps the system icons. The light/dark mode (Apparence) is separate
 * and works with every theme.
 */

#include <windows.h>
#include <shellapi.h>
#include <shlobj.h>
#include <uxtheme.h>
#include <uxundoc.h>
#include <strsafe.h>

#define IDC_CARD0       100
#define IDC_STATUS      200
#define IDC_MODE        201
#define IDC_CLOSE       IDCANCEL
#define NTHEMES         5
#define CARD_W          104
#define CARD_H          150
#define ICONS_KEY       L"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\CLSID\\"
#define MADOS_KEY       L"Software\\MadOS\\Themes"

typedef struct
{
    PCWSTR Dir;
    PCWSTR File;
    PCWSTR Wallpaper;
    BOOL Icons;
    PCWSTR Fr;
    PCWSTR En;
    COLORREF Accent;
    COLORREF Desktop;
} THEME;

static const THEME Themes[NTHEMES] =
{
    { L"Aero",      L"aero.msstyles",      L"MadOS.png",           FALSE, L"Braise",    L"Ember",    RGB(239, 68, 68),  RGB(28, 25, 23) },
    { L"Ocean",     L"Ocean.msstyles",     L"MadOS-Ocean.png",     TRUE,  L"Océan",     L"Ocean",    RGB(59, 130, 246), RGB(15, 23, 42) },
    { L"Foret",     L"Foret.msstyles",     L"MadOS-Foret.png",     TRUE,  L"Forêt",     L"Forest",   RGB(16, 185, 129), RGB(17, 26, 22) },
    { L"Amethyste", L"Amethyste.msstyles", L"MadOS-Amethyste.png", TRUE,  L"Améthyste", L"Amethyst", RGB(168, 85, 247), RGB(24, 20, 32) },
    { L"Ambre",     L"Ambre.msstyles",     L"MadOS-Ambre.png",     TRUE,  L"Ambre",     L"Amber",    RGB(245, 158, 11), RGB(28, 25, 23) },
};

/* Desktop items whose icon follows the theme: CLSID, registry value, file */
static const struct { PCWSTR Clsid; PCWSTR Value; PCWSTR File; } Icons[] =
{
    { L"{20D04FE0-3AEA-1069-A2D8-08002B30309D}", NULL,     L"computer.ico" },
    { L"{450D8FBA-AD25-11D0-98A8-0800361B1103}", NULL,     L"documents.ico" },
    { L"{208D2C60-3AEA-1069-A2D7-08002B30309D}", NULL,     L"network.ico" },
    { L"{645FF040-5081-101B-9F08-00AA002F954E}", NULL,     L"trash-empty.ico" },
    { L"{645FF040-5081-101B-9F08-00AA002F954E}", L"Empty", L"trash-empty.ico" },
    { L"{645FF040-5081-101B-9F08-00AA002F954E}", L"Full",  L"trash-full.ico" },
};

static HINSTANCE hInst;
static HWND hStatus;
static HFONT hTitleFont, hTextFont, hNameFont;
static BOOL French;
static int Current = -1;

static PCWSTR T(PCWSTR fr, PCWSTR en) { return French ? fr : en; }
static PCWSTR Name(int i) { return French ? Themes[i].Fr : Themes[i].En; }

static void ThemePath(int i, PWSTR Path, SIZE_T cch)
{
    GetWindowsDirectoryW(Path, (UINT)cch);
    StringCchCatW(Path, cch, L"\\Resources\\Themes\\");
    StringCchCatW(Path, cch, Themes[i].Dir);
    StringCchCatW(Path, cch, L"\\");
}

static int FindCurrent(void)
{
    WCHAR Path[MAX_PATH], Dir[MAX_PATH];
    int i;

    if (FAILED(GetCurrentThemeName(Path, ARRAYSIZE(Path), NULL, 0, NULL, 0)))
        return -1;
    for (i = 0; i < NTHEMES; i++)
    {
        ThemePath(i, Dir, ARRAYSIZE(Dir));
        if (_wcsnicmp(Path, Dir, wcslen(Dir)) == 0)
            return i;
    }
    return -1;
}

static void SetIcons(int i)
{
    WCHAR Key[160], Value[MAX_PATH];
    HKEY h;
    UINT n;

    for (n = 0; n < ARRAYSIZE(Icons); n++)
    {
        StringCchPrintfW(Key, ARRAYSIZE(Key), ICONS_KEY L"%s\\DefaultIcon", Icons[n].Clsid);
        if (!Themes[i].Icons)
        {
            RegDeleteKeyW(HKEY_CURRENT_USER, Key);
            continue;
        }
        ThemePath(i, Value, ARRAYSIZE(Value));
        StringCchCatW(Value, ARRAYSIZE(Value), L"Icons\\");
        StringCchCatW(Value, ARRAYSIZE(Value), Icons[n].File);
        StringCchCatW(Value, ARRAYSIZE(Value), L",0");
        if (RegCreateKeyExW(HKEY_CURRENT_USER, Key, 0, NULL, 0, KEY_SET_VALUE, NULL, &h, NULL) == ERROR_SUCCESS)
        {
            RegSetValueExW(h, Icons[n].Value, 0, REG_SZ, (const BYTE *)Value,
                           (DWORD)((wcslen(Value) + 1) * sizeof(WCHAR)));
            RegCloseKey(h);
        }
    }
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);
}

static BOOL Apply(HWND hwnd, int i)
{
    WCHAR Style[MAX_PATH], Color[MAX_PATH] = L"", Size[MAX_PATH] = L"", Wallpaper[MAX_PATH], Old[MAX_PATH];
    WCHAR Text[256];
    HCURSOR Cursor;
    HRESULT hr;
    HKEY h;

    ThemePath(i, Style, ARRAYSIZE(Style));
    StringCchCatW(Style, ARRAYSIZE(Style), Themes[i].File);
    if (GetFileAttributesW(Style) == INVALID_FILE_ATTRIBUTES)
    {
        StringCchPrintfW(Text, ARRAYSIZE(Text), T(L"Le thème %s n'est pas installé.", L"The %s theme is not installed."), Name(i));
        SetWindowTextW(hStatus, Text);
        return FALSE;
    }

    Cursor = SetCursor(LoadCursorW(NULL, IDC_WAIT));
    SetWindowTextW(hStatus, T(L"Application du thème…", L"Applying the theme…"));
    UpdateWindow(hStatus);

    /* Keep the current colour scheme and size (all MadOS themes have the
     * same ones), or the defaults of the new style. */
    if (FAILED(GetCurrentThemeName(Old, ARRAYSIZE(Old), Color, ARRAYSIZE(Color), Size, ARRAYSIZE(Size))))
        GetThemeDefaults(Style, Color, ARRAYSIZE(Color), Size, ARRAYSIZE(Size));
    hr = SetSystemVisualStyle(Style, Color[0] ? Color : NULL, Size[0] ? Size : NULL, 0);
    if (FAILED(hr))
    {
        GetThemeDefaults(Style, Color, ARRAYSIZE(Color), Size, ARRAYSIZE(Size));
        hr = SetSystemVisualStyle(Style, Color, Size, 0);
    }

    GetWindowsDirectoryW(Wallpaper, ARRAYSIZE(Wallpaper));
    StringCchCatW(Wallpaper, ARRAYSIZE(Wallpaper), L"\\Web\\Wallpaper\\");
    StringCchCatW(Wallpaper, ARRAYSIZE(Wallpaper), Themes[i].Wallpaper);
    if (GetFileAttributesW(Wallpaper) != INVALID_FILE_ATTRIBUTES)
        SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, Wallpaper, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE);

    SetIcons(i);

    if (RegCreateKeyExW(HKEY_CURRENT_USER, MADOS_KEY, 0, NULL, 0, KEY_SET_VALUE, NULL, &h, NULL) == ERROR_SUCCESS)
    {
        RegSetValueExW(h, L"Current", 0, REG_SZ, (const BYTE *)Themes[i].Dir,
                       (DWORD)((wcslen(Themes[i].Dir) + 1) * sizeof(WCHAR)));
        RegCloseKey(h);
    }
    SetCursor(Cursor);

    if (FAILED(hr))
        StringCchPrintfW(Text, ARRAYSIZE(Text),
                         T(L"Le style des fenêtres n'a pas pu être changé (erreur 0x%08lX). Le fond d'écran et les icônes sont appliqués.",
                           L"The window style could not be changed (error 0x%08lX). The wallpaper and icons are applied."), hr);
    else
        StringCchPrintfW(Text, ARRAYSIZE(Text), T(L"Thème %s appliqué.", L"%s theme applied."), Name(i));
    SetWindowTextW(hStatus, Text);
    Current = i;
    InvalidateRect(hwnd, NULL, FALSE);
    return SUCCEEDED(hr);
}

static void Rounded(HDC dc, int l, int t, int r, int b, int rad, COLORREF Fill, COLORREF Line, int Width)
{
    HBRUSH Brush = CreateSolidBrush(Fill);
    HPEN Pen = CreatePen(PS_SOLID, Width, Line);
    HGDIOBJ ob = SelectObject(dc, Brush), op = SelectObject(dc, Pen);
    RoundRect(dc, l, t, r, b, rad, rad);
    SelectObject(dc, ob);
    SelectObject(dc, op);
    DeleteObject(Brush);
    DeleteObject(Pen);
}

static COLORREF Mix(COLORREF a, COLORREF b, int Pct)
{
    return RGB((GetRValue(a) * (100 - Pct) + GetRValue(b) * Pct) / 100,
               (GetGValue(a) * (100 - Pct) + GetGValue(b) * Pct) / 100,
               (GetBValue(a) * (100 - Pct) + GetBValue(b) * Pct) / 100);
}

/* A card: small preview of the desktop (background, glow, badge) and the
 * theme's name; the current theme has an accent frame. */
static void DrawCard(const DRAWITEMSTRUCT *di)
{
    int i = (int)di->CtlID - IDC_CARD0;
    const THEME *t = &Themes[i];
    HDC dc = di->hDC;
    RECT rc = di->rcItem, pv, tx;
    BOOL Sel = (i == Current);
    int k;

    FillRect(dc, &rc, GetSysColorBrush(COLOR_BTNFACE));
    Rounded(dc, rc.left + 1, rc.top + 1, rc.right - 1, rc.bottom - 1, 12,
            GetSysColor(COLOR_WINDOW), Sel ? t->Accent : GetSysColor(COLOR_3DSHADOW), Sel ? 3 : 1);

    pv.left = rc.left + 8; pv.top = rc.top + 8; pv.right = rc.right - 8; pv.bottom = pv.top + 84;
    Rounded(dc, pv.left, pv.top, pv.right, pv.bottom, 8, t->Desktop, t->Desktop, 1);
    /* glow in the lower right corner, as on the wallpaper */
    for (k = 0; k < 4; k++)
    {
        int r = 34 - k * 8;
        Rounded(dc, pv.right - 10 - r, pv.bottom - 4 - r / 2, pv.right - 10 + r / 2, pv.bottom - 2, r,
                Mix(t->Desktop, t->Accent, 15 + k * 12), Mix(t->Desktop, t->Accent, 15 + k * 12), 1);
    }
    /* badge */
    Rounded(dc, (pv.left + pv.right) / 2 - 16, pv.top + 14, (pv.left + pv.right) / 2 + 16, pv.top + 46, 10,
            t->Accent, t->Accent, 1);
    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, RGB(255, 255, 255));
    SelectObject(dc, hNameFont);
    tx.left = pv.left; tx.right = pv.right; tx.top = pv.top + 14; tx.bottom = pv.top + 46;
    DrawTextW(dc, L"M", 1, &tx, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
    /* taskbar */
    tx = pv; tx.top = pv.bottom - 10; tx.bottom = pv.bottom - 2; tx.left += 2; tx.right -= 2;
    Rounded(dc, tx.left, tx.top, tx.right, tx.bottom, 4, Mix(t->Desktop, RGB(0, 0, 0), 40), Mix(t->Desktop, RGB(0, 0, 0), 40), 1);
    Rounded(dc, tx.left + 3, tx.top + 1, tx.left + 10, tx.bottom - 1, 3, t->Accent, t->Accent, 1);

    tx.left = rc.left + 4; tx.right = rc.right - 4; tx.top = pv.bottom + 8; tx.bottom = rc.bottom - 26;
    SetTextColor(dc, GetSysColor(COLOR_WINDOWTEXT));
    DrawTextW(dc, Name(i), -1, &tx, DT_CENTER | DT_SINGLELINE | DT_VCENTER);
    if (Sel)
    {
        SelectObject(dc, hTextFont);
        SetTextColor(dc, t->Accent);
        tx.top = tx.bottom; tx.bottom = rc.bottom - 6;
        DrawTextW(dc, T(L"Actuel", L"Current"), -1, &tx, DT_CENTER | DT_SINGLELINE | DT_VCENTER);
    }
    if (di->itemState & ODS_FOCUS)
    {
        RECT f = rc;
        InflateRect(&f, -5, -5);
        DrawFocusRect(dc, &f);
    }
}

static void CreateControls(HWND hwnd)
{
    HWND h;
    int i;

    hTitleFont = CreateFontW(-26, 0, 0, 0, FW_SEMIBOLD, 0, 0, 0, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Segoe UI");
    hTextFont = CreateFontW(-14, 0, 0, 0, FW_NORMAL, 0, 0, 0, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Segoe UI");
    hNameFont = CreateFontW(-16, 0, 0, 0, FW_SEMIBOLD, 0, 0, 0, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Segoe UI");

    h = CreateWindowW(L"STATIC", T(L"Thèmes", L"Themes"), WS_CHILD | WS_VISIBLE,
                      24, 18, 560, 36, hwnd, NULL, hInst, NULL);
    SendMessageW(h, WM_SETFONT, (WPARAM)hTitleFont, TRUE);
    h = CreateWindowW(L"STATIC",
                      T(L"Choisissez un thème : couleurs des fenêtres, fond d'écran, bouton Démarrer et icônes "
                        L"du bureau. Il s'applique tout de suite. Le mode clair ou sombre reste au choix.",
                        L"Choose a theme: window colors, wallpaper, Start button and desktop icons. It is "
                        L"applied right away. The light or dark mode stays your choice."),
                      WS_CHILD | WS_VISIBLE, 24, 60, 560, 40, hwnd, NULL, hInst, NULL);
    SendMessageW(h, WM_SETFONT, (WPARAM)hTextFont, TRUE);

    for (i = 0; i < NTHEMES; i++)
    {
        h = CreateWindowW(L"BUTTON", Name(i), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_OWNERDRAW,
                          24 + i * (CARD_W + 10), 112, CARD_W, CARD_H, hwnd, (HMENU)(INT_PTR)(IDC_CARD0 + i), hInst, NULL);
        SendMessageW(h, WM_SETFONT, (WPARAM)hNameFont, TRUE);
    }

    hStatus = CreateWindowW(L"STATIC", L"", WS_CHILD | WS_VISIBLE, 24, 276, 560, 36, hwnd, (HMENU)IDC_STATUS, hInst, NULL);
    SendMessageW(hStatus, WM_SETFONT, (WPARAM)hTextFont, TRUE);

    h = CreateWindowW(L"BUTTON", T(L"Mode clair ou sombre…", L"Light or dark mode…"), WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                      24, 322, 190, 30, hwnd, (HMENU)IDC_MODE, hInst, NULL);
    SendMessageW(h, WM_SETFONT, (WPARAM)hTextFont, TRUE);
    h = CreateWindowW(L"BUTTON", T(L"Fermer", L"Close"), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_DEFPUSHBUTTON,
                      484, 322, 100, 30, hwnd, (HMENU)IDC_CLOSE, hInst, NULL);
    SendMessageW(h, WM_SETFONT, (WPARAM)hTextFont, TRUE);

    SetFocus(GetDlgItem(hwnd, IDC_CARD0 + (Current >= 0 ? Current : 0)));
}

static LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
    switch (msg)
    {
        case WM_CREATE:
            Current = FindCurrent();
            CreateControls(hwnd);
            return 0;

        case WM_DRAWITEM:
        {
            const DRAWITEMSTRUCT *di = (const DRAWITEMSTRUCT *)lParam;
            if (di->CtlID >= IDC_CARD0 && di->CtlID < IDC_CARD0 + NTHEMES)
            {
                DrawCard(di);
                return TRUE;
            }
            break;
        }

        case WM_COMMAND:
        {
            UINT id = LOWORD(wParam);
            if (id >= IDC_CARD0 && id < IDC_CARD0 + NTHEMES && HIWORD(wParam) == BN_CLICKED)
            {
                Apply(hwnd, (int)(id - IDC_CARD0));
                return 0;
            }
            if (id == IDC_MODE)
            {
                ShellExecuteW(hwnd, NULL, L"dwmsettings.exe", NULL, NULL, SW_SHOWNORMAL);
                return 0;
            }
            if (id == IDC_CLOSE)
            {
                DestroyWindow(hwnd);
                return 0;
            }
            break;
        }

        case WM_THEMECHANGED:
            Current = FindCurrent();
            InvalidateRect(hwnd, NULL, TRUE);
            break;

        case WM_DESTROY:
            DeleteObject(hTitleFont);
            DeleteObject(hTextFont);
            DeleteObject(hNameFont);
            PostQuitMessage(0);
            return 0;
    }
    return DefWindowProcW(hwnd, msg, wParam, lParam);
}

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrev, PWSTR CmdLine, int nShow)
{
    WNDCLASSEXW wc = { sizeof(wc) };
    RECT rc = { 0, 0, 608, 372 };
    MSG msg;
    HWND hwnd;

    UNREFERENCED_PARAMETER(hPrev);
    UNREFERENCED_PARAMETER(CmdLine);
    hInst = hInstance;
    French = PRIMARYLANGID(GetUserDefaultUILanguage()) == LANG_FRENCH;

    hwnd = FindWindowW(L"MadOSThemes", NULL);
    if (hwnd)
    {
        ShowWindow(hwnd, SW_RESTORE);
        SetForegroundWindow(hwnd);
        return 0;
    }

    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.hCursor = LoadCursorW(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_BTNFACE + 1);
    wc.hIcon = LoadIconW(hInstance, MAKEINTRESOURCEW(1));
    wc.lpszClassName = L"MadOSThemes";
    RegisterClassExW(&wc);

    AdjustWindowRect(&rc, WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX, FALSE);
    hwnd = CreateWindowW(wc.lpszClassName, T(L"Thèmes", L"Themes"),
                         WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
                         CW_USEDEFAULT, CW_USEDEFAULT, rc.right - rc.left, rc.bottom - rc.top,
                         NULL, NULL, hInstance, NULL);
    if (!hwnd)
        return 1;
    ShowWindow(hwnd, nShow);
    UpdateWindow(hwnd);

    while (GetMessageW(&msg, NULL, 0, 0))
    {
        if (!IsDialogMessageW(hwnd, &msg))
        {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
    }
    return (int)msg.wParam;
}
