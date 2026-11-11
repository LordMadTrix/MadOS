/*
 * PROJECT:     MadOS
 * LICENSE:     GPL-3.0-or-later (https://spdx.org/licenses/GPL-3.0-or-later)
 * PURPOSE:     "Bienvenue dans MadOS" - choose the applications to install
 *
 * Shows a short list of applications (madapps.ini) with check boxes. Each
 * selected application is downloaded from its publisher's official site,
 * verified (valid Authenticode signature issued to the expected publisher, or
 * pinned SHA-256 for unsigned installers) and installed silently. Nothing is
 * run if the verification fails.
 *
 * Started once per machine after the first-boot setup (RunOnce), and from the
 * Start menu at any time.
 */

#include <windows.h>
#include <commctrl.h>
#include <shellapi.h>
#include <shlwapi.h>
#include <tlhelp32.h>
#include <urlmon.h>
#include <wincrypt.h>
#include <wintrust.h>
#include <softpub.h>
#include <bcrypt.h>
#include <strsafe.h>
#include <stdlib.h>

#define MAX_APPS        16
#define IDC_LIST        101
#define IDC_INSTALL     IDOK        /* Entree : installer */
#define IDC_CLOSE       IDCANCEL    /* Echap : passer / terminer */
#define WM_APP_STATUS   (WM_APP + 1)
#define WM_APP_DONE     (WM_APP + 2)
#define MADOS_KEY       L"SOFTWARE\\MadOS\\Welcome"

typedef enum
{
    ST_NONE, ST_INSTALLED_BEFORE, ST_WAITING, ST_DOWNLOADING, ST_VERIFYING,
    ST_INSTALLING, ST_DONE, ST_ERR_DOWNLOAD, ST_ERR_VERIFY, ST_ERR_INSTALL, ST_COUNT
} APP_STATE;

typedef struct
{
    WCHAR Key[32];
    WCHAR Name[64];
    WCHAR Desc[128];
    WCHAR Url[512];
    WCHAR Type[8];
    WCHAR Args[128];
    WCHAR Signer[128];
    WCHAR Sha256[80];
    WCHAR Check[MAX_PATH];
    BOOL Default;
} APP;

static HINSTANCE hInst;
static HWND hMain, hList, hInstall, hClose;
static HFONT hTitleFont, hTextFont;
static APP Apps[MAX_APPS];
static int AppCount;
static BOOL French, Busy;
static WCHAR IniPath[MAX_PATH];

/* ------------------------------------------------------------- texts ---- */

static PCWSTR T(PCWSTR fr, PCWSTR en) { return French ? fr : en; }

static PCWSTR StateText(APP_STATE s)
{
    static const PCWSTR Fr[ST_COUNT] = {
        L"", L"Déjà installée", L"En attente", L"Téléchargement…", L"Vérification…",
        L"Installation…", L"Installée", L"Échec du téléchargement", L"Vérification refusée",
        L"Échec de l'installation" };
    static const PCWSTR En[ST_COUNT] = {
        L"", L"Already installed", L"Waiting", L"Downloading…", L"Verifying…",
        L"Installing…", L"Installed", L"Download failed", L"Verification refused",
        L"Installation failed" };
    return (French ? Fr : En)[s];
}

/* ---------------------------------------------------------- manifest ---- */

static void IniText(PCWSTR Section, PCWSTR Key, PWSTR Out, DWORD Cch)
{
    WCHAR Raw[512];
    GetPrivateProfileStringW(Section, Key, L"", Raw, ARRAYSIZE(Raw), IniPath);
    if (!ExpandEnvironmentStringsW(Raw, Out, Cch))
        StringCchCopyW(Out, Cch, Raw);
}

static void LoadApps(void)
{
    WCHAR Order[512], *Ctx = NULL, *Tok;
    APP *A;

    GetPrivateProfileStringW(L"Apps", L"Order", L"", Order, ARRAYSIZE(Order), IniPath);
    for (Tok = wcstok_s(Order, L",", &Ctx); Tok && AppCount < MAX_APPS; Tok = wcstok_s(NULL, L",", &Ctx))
    {
        while (*Tok == L' ') Tok++;
        A = &Apps[AppCount];
        ZeroMemory(A, sizeof(*A));
        StringCchCopyW(A->Key, ARRAYSIZE(A->Key), Tok);
        IniText(Tok, L"Name", A->Name, ARRAYSIZE(A->Name));
        IniText(Tok, French ? L"Desc.fr" : L"Desc.en", A->Desc, ARRAYSIZE(A->Desc));
        IniText(Tok, L"Url", A->Url, ARRAYSIZE(A->Url));
        IniText(Tok, L"Type", A->Type, ARRAYSIZE(A->Type));
        IniText(Tok, L"Args", A->Args, ARRAYSIZE(A->Args));
        IniText(Tok, L"Signer", A->Signer, ARRAYSIZE(A->Signer));
        IniText(Tok, L"Sha256", A->Sha256, ARRAYSIZE(A->Sha256));
        IniText(Tok, L"Check", A->Check, ARRAYSIZE(A->Check));
        A->Default = GetPrivateProfileIntW(Tok, L"Default", 0, IniPath) != 0;
        if (A->Name[0] && A->Url[0] && (A->Signer[0] || A->Sha256[0]))
            AppCount++;
    }
}

/* -------------------------------------------------------- verification -- */

/* Valid Authenticode signature AND issued to the expected publisher. */
static BOOL VerifySigner(PCWSTR File, PCWSTR Expected)
{
    GUID Action = WINTRUST_ACTION_GENERIC_VERIFY_V2;
    WINTRUST_FILE_INFO FileInfo = { sizeof(FileInfo) };
    WINTRUST_DATA Data = { sizeof(Data) };
    CRYPT_PROVIDER_DATA *Prov;
    CRYPT_PROVIDER_SGNR *Signer;
    CRYPT_PROVIDER_CERT *Cert;
    WCHAR Name[256];
    BOOL Ok = FALSE;

    FileInfo.pcwszFilePath = File;
    Data.dwUIChoice = WTD_UI_NONE;
    Data.fdwRevocationChecks = WTD_REVOKE_NONE;
    Data.dwUnionChoice = WTD_CHOICE_FILE;
    Data.pFile = &FileInfo;
    Data.dwStateAction = WTD_STATEACTION_VERIFY;

    if (WinVerifyTrust(NULL, &Action, &Data) == ERROR_SUCCESS)
    {
        Prov = WTHelperProvDataFromStateData(Data.hWVTStateData);
        Signer = Prov ? WTHelperGetProvSignerFromChain(Prov, 0, FALSE, 0) : NULL;
        Cert = Signer ? WTHelperGetProvCertFromChain(Signer, 0) : NULL;
        if (Cert && CertGetNameStringW(Cert->pCert, CERT_NAME_SIMPLE_DISPLAY_TYPE, 0, NULL, Name, ARRAYSIZE(Name)))
            Ok = (StrStrIW(Name, Expected) != NULL);
    }

    Data.dwStateAction = WTD_STATEACTION_CLOSE;
    WinVerifyTrust(NULL, &Action, &Data);
    return Ok;
}

static BOOL VerifySha256(PCWSTR File, PCWSTR Expected)
{
    BCRYPT_ALG_HANDLE Alg = NULL;
    BCRYPT_HASH_HANDLE Hash = NULL;
    BYTE Digest[32], Buffer[64 * 1024];
    WCHAR Hex[65];
    HANDLE h;
    DWORD Read, i;
    BOOL Ok = FALSE;

    h = CreateFileW(File, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (h == INVALID_HANDLE_VALUE)
        return FALSE;
    if (BCryptOpenAlgorithmProvider(&Alg, BCRYPT_SHA256_ALGORITHM, NULL, 0) == 0 &&
        BCryptCreateHash(Alg, &Hash, NULL, 0, NULL, 0, 0) == 0)
    {
        while (ReadFile(h, Buffer, sizeof(Buffer), &Read, NULL) && Read)
            BCryptHashData(Hash, Buffer, Read, 0);
        if (BCryptFinishHash(Hash, Digest, sizeof(Digest), 0) == 0)
        {
            for (i = 0; i < 32; i++)
                StringCchPrintfW(Hex + i * 2, 3, L"%02x", Digest[i]);
            Ok = (_wcsicmp(Hex, Expected) == 0);
        }
    }
    if (Hash) BCryptDestroyHash(Hash);
    if (Alg) BCryptCloseAlgorithmProvider(Alg, 0);
    CloseHandle(h);
    return Ok;
}

/* ------------------------------------------------------------ install ---- */

static BOOL RunAndWait(PWSTR CommandLine)
{
    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    if (!CreateProcessW(NULL, CommandLine, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi))
        return FALSE;
    WaitForSingleObject(pi.hProcess, INFINITE);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return TRUE;
}

static void Status(int Index, APP_STATE s) { PostMessageW(hMain, WM_APP_STATUS, Index, s); }

static DWORD WINAPI InstallThread(LPVOID Param)
{
    WCHAR Dir[MAX_PATH], File[MAX_PATH], Cmd[MAX_PATH * 2];
    BOOL *Selected = (BOOL *)Param;
    int i;

    GetTempPathW(ARRAYSIZE(Dir), Dir);
    StringCchCatW(Dir, ARRAYSIZE(Dir), L"MadOS-Bienvenue");
    CreateDirectoryW(Dir, NULL);

    for (i = 0; i < AppCount; i++)
        if (Selected[i])
            Status(i, ST_WAITING);

    for (i = 0; i < AppCount; i++)
    {
        APP *A = &Apps[i];
        BOOL Verified;

        if (!Selected[i])
            continue;

        /* "<key>-setup.exe", never "<key>.exe": some installers (VLC) refuse
         * to run while a process with the application's name is running, and
         * would see themselves. */
        StringCchPrintfW(File, ARRAYSIZE(File), L"%s\\%s-setup.%s", Dir, A->Key,
                         _wcsicmp(A->Type, L"msi") == 0 ? L"msi" : L"exe");
        Status(i, ST_DOWNLOADING);
        DeleteFileW(File);
        if (FAILED(URLDownloadToFileW(NULL, A->Url, File, 0, NULL)))
        {
            Status(i, ST_ERR_DOWNLOAD);
            continue;
        }

        Status(i, ST_VERIFYING);
        Verified = A->Sha256[0] ? VerifySha256(File, A->Sha256) : VerifySigner(File, A->Signer);
        if (!Verified)
        {
            DeleteFileW(File);
            Status(i, ST_ERR_VERIFY);
            continue;
        }

        Status(i, ST_INSTALLING);
        if (_wcsicmp(A->Type, L"msi") == 0)
            StringCchPrintfW(Cmd, ARRAYSIZE(Cmd), L"msiexec.exe /i \"%s\" /qn /norestart", File);
        else
            StringCchPrintfW(Cmd, ARRAYSIZE(Cmd), L"\"%s\" %s", File, A->Args);
        RunAndWait(Cmd);
        DeleteFileW(File);

        Status(i, GetFileAttributesW(A->Check) != INVALID_FILE_ATTRIBUTES ? ST_DONE : ST_ERR_INSTALL);
    }

    RemoveDirectoryW(Dir);
    HeapFree(GetProcessHeap(), 0, Selected);
    PostMessageW(hMain, WM_APP_DONE, 0, 0);
    return 0;
}

/* ----------------------------------------------------------------- UI ---- */

static int CheckedCount(void)
{
    int i, n = 0;
    for (i = 0; i < AppCount; i++)
        n += ListView_GetCheckState(hList, i) ? 1 : 0;
    return n;
}

static void UpdateInstallButton(void)
{
    WCHAR Text[64];
    int n = CheckedCount();
    StringCchPrintfW(Text, ARRAYSIZE(Text), T(L"Installer (%d)", L"Install (%d)"), n);
    SetWindowTextW(hInstall, Text);
    EnableWindow(hInstall, n > 0 && !Busy);
}

static void SetState(int Index, APP_STATE s)
{
    ListView_SetItemText(hList, Index, 2, (PWSTR)StateText(s));
}

static void StartInstall(void)
{
    BOOL *Selected = HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, sizeof(BOOL) * MAX_APPS);
    HANDLE Thread;
    int i;

    if (!Selected)
        return;
    for (i = 0; i < AppCount; i++)
        Selected[i] = ListView_GetCheckState(hList, i);

    Busy = TRUE;
    EnableWindow(hList, FALSE);
    EnableWindow(hInstall, FALSE);
    EnableWindow(hClose, FALSE);
    Thread = CreateThread(NULL, 0, InstallThread, Selected, 0, NULL);
    if (Thread)
        CloseHandle(Thread);
}

static void MarkDone(void)
{
    HKEY Key;
    DWORD One = 1;
    if (RegCreateKeyExW(HKEY_LOCAL_MACHINE, MADOS_KEY, 0, NULL, 0, KEY_SET_VALUE, NULL, &Key, NULL) == ERROR_SUCCESS)
    {
        RegSetValueExW(Key, L"Done", 0, REG_DWORD, (const BYTE *)&One, sizeof(One));
        RegCloseKey(Key);
    }
}

static void CreateControls(HWND hwnd)
{
    LVCOLUMNW Col = { LVCF_TEXT | LVCF_WIDTH };
    LVITEMW Item = { LVIF_TEXT };
    HWND h;
    int i;

    hTitleFont = CreateFontW(-26, 0, 0, 0, FW_SEMIBOLD, 0, 0, 0, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Segoe UI");
    hTextFont = CreateFontW(-14, 0, 0, 0, FW_NORMAL, 0, 0, 0, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Segoe UI");

    h = CreateWindowW(L"STATIC", T(L"Bienvenue dans MadOS", L"Welcome to MadOS"), WS_CHILD | WS_VISIBLE,
                      24, 18, 560, 36, hwnd, NULL, hInst, NULL);
    SendMessageW(h, WM_SETFONT, (WPARAM)hTitleFont, TRUE);
    h = CreateWindowW(L"STATIC",
                      T(L"Choisissez les applications à installer. Elles sont téléchargées depuis le site officiel "
                        L"de chaque éditeur et vérifiées avant l'installation. Une connexion Internet est nécessaire.",
                        L"Choose the applications to install. They are downloaded from each publisher's official "
                        L"site and verified before installation. An Internet connection is required."),
                      WS_CHILD | WS_VISIBLE, 24, 60, 560, 40, hwnd, NULL, hInst, NULL);
    SendMessageW(h, WM_SETFONT, (WPARAM)hTextFont, TRUE);

    hList = CreateWindowExW(WS_EX_CLIENTEDGE, WC_LISTVIEWW, L"",
                            WS_CHILD | WS_VISIBLE | WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_NOSORTHEADER,
                            24, 110, 560, 236, hwnd, (HMENU)IDC_LIST, hInst, NULL);
    ListView_SetExtendedListViewStyle(hList, LVS_EX_CHECKBOXES | LVS_EX_FULLROWSELECT);
    SendMessageW(hList, WM_SETFONT, (WPARAM)hTextFont, TRUE);
    Col.cx = 150; Col.pszText = (PWSTR)T(L"Application", L"Application"); ListView_InsertColumn(hList, 0, &Col);
    Col.cx = 240; Col.pszText = (PWSTR)T(L"Description", L"Description"); ListView_InsertColumn(hList, 1, &Col);
    Col.cx = 160; Col.pszText = (PWSTR)T(L"État", L"Status"); ListView_InsertColumn(hList, 2, &Col);

    for (i = 0; i < AppCount; i++)
    {
        BOOL Installed = GetFileAttributesW(Apps[i].Check) != INVALID_FILE_ATTRIBUTES;
        Item.iItem = i;
        Item.pszText = Apps[i].Name;
        ListView_InsertItem(hList, &Item);
        ListView_SetItemText(hList, i, 1, Apps[i].Desc);
        ListView_SetItemText(hList, i, 2, (PWSTR)StateText(Installed ? ST_INSTALLED_BEFORE : ST_NONE));
        ListView_SetCheckState(hList, i, Apps[i].Default && !Installed);
    }

    hClose = CreateWindowW(L"BUTTON", T(L"Passer", L"Skip"), WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                           360, 362, 100, 30, hwnd, (HMENU)IDC_CLOSE, hInst, NULL);
    hInstall = CreateWindowW(L"BUTTON", L"", WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_DEFPUSHBUTTON,
                             470, 362, 114, 30, hwnd, (HMENU)IDC_INSTALL, hInst, NULL);
    SendMessageW(hClose, WM_SETFONT, (WPARAM)hTextFont, TRUE);
    SendMessageW(hInstall, WM_SETFONT, (WPARAM)hTextFont, TRUE);
    UpdateInstallButton();

    /* Keyboard: the list has the focus (arrows + Space to tick), Enter
     * installs (IDOK), Escape skips (IDCANCEL). */
    if (AppCount > 0)
        ListView_SetItemState(hList, 0, LVIS_FOCUSED, LVIS_FOCUSED);
    SetFocus(hList);
}

static LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
    switch (msg)
    {
        case WM_CREATE:
            hMain = hwnd;
            CreateControls(hwnd);
            return 0;

        case WM_NOTIFY:
            if (((LPNMHDR)lParam)->idFrom == IDC_LIST && ((LPNMHDR)lParam)->code == LVN_ITEMCHANGED && !Busy)
                UpdateInstallButton();
            return 0;

        case WM_COMMAND:
            if (LOWORD(wParam) == IDC_INSTALL && !Busy)
                StartInstall();
            else if (LOWORD(wParam) == IDC_CLOSE && !Busy)
                DestroyWindow(hwnd);
            return 0;

        case WM_APP_STATUS:
            SetState((int)wParam, (APP_STATE)lParam);
            return 0;

        case WM_APP_DONE:
            Busy = FALSE;
            MarkDone();
            SetWindowTextW(hClose, T(L"Terminer", L"Finish"));
            EnableWindow(hClose, TRUE);
            EnableWindow(hList, TRUE);
            UpdateInstallButton();
            return 0;

        case WM_CLOSE:
            if (!Busy)
                DestroyWindow(hwnd);
            return 0;

        case WM_DESTROY:
            if (!Busy)
                MarkDone();
            PostQuitMessage(0);
            return 0;
    }
    return DefWindowProcW(hwnd, msg, wParam, lParam);
}

/* -------------------------------------------------------------- start ---- */

static BOOL SetupRunning(void)
{
    static const PCWSTR Names[] = { L"oobe.exe", L"libernt.exe", L"setup.exe" };
    PROCESSENTRY32W pe = { sizeof(pe) };
    HANDLE Snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    BOOL Found = FALSE;
    int i;

    if (Snap == INVALID_HANDLE_VALUE)
        return FALSE;
    if (Process32FirstW(Snap, &pe))
    {
        do
        {
            for (i = 0; i < ARRAYSIZE(Names); i++)
                Found |= (_wcsicmp(pe.szExeFile, Names[i]) == 0);
        } while (!Found && Process32NextW(Snap, &pe));
    }
    CloseHandle(Snap);
    return Found;
}

static BOOL AlreadyDone(void)
{
    DWORD Done = 0, Size = sizeof(Done), Type = 0;
    HKEY Key;
    BOOL Result = FALSE;

    if (RegOpenKeyExW(HKEY_LOCAL_MACHINE, MADOS_KEY, 0, KEY_QUERY_VALUE, &Key) == ERROR_SUCCESS)
    {
        Result = RegQueryValueExW(Key, L"Done", NULL, &Type, (LPBYTE)&Done, &Size) == ERROR_SUCCESS &&
                 Type == REG_DWORD && Done != 0;
        RegCloseKey(Key);
    }
    return Result;
}

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrev, PWSTR CmdLine, int nShow)
{
    INITCOMMONCONTROLSEX icc = { sizeof(icc), ICC_LISTVIEW_CLASSES };
    WNDCLASSEXW wc = { sizeof(wc) };
    RECT rc = { 0, 0, 608, 412 };
    MSG msg;
    HWND hwnd;
    PWSTR Slash;

    UNREFERENCED_PARAMETER(hPrev);
    hInst = hInstance;
    French = PRIMARYLANGID(GetUserDefaultUILanguage()) == LANG_FRENCH;

    /* One window only: a second start brings the existing one to the front
     * (two windows could install the same application twice). */
    CreateMutexW(NULL, TRUE, L"Local\\MadOSWelcome");
    if (GetLastError() == ERROR_ALREADY_EXISTS)
    {
        hwnd = FindWindowW(L"MadOSWelcome", NULL);
        if (hwnd)
        {
            ShowWindow(hwnd, SW_RESTORE);
            SetForegroundWindow(hwnd);
        }
        return 0;
    }

    /* "/firstrun": started by RunOnce after setup. Wait for the first-boot
     * setup to finish, and do nothing if the welcome was already used. */
    if (CmdLine && StrStrIW(CmdLine, L"/firstrun"))
    {
        while (SetupRunning())
            Sleep(2000);
        if (AlreadyDone())
            return 0;
        French = PRIMARYLANGID(GetUserDefaultUILanguage()) == LANG_FRENCH;
    }

    GetModuleFileNameW(NULL, IniPath, ARRAYSIZE(IniPath));
    Slash = wcsrchr(IniPath, L'\\');
    StringCchCopyW(Slash ? Slash + 1 : IniPath, MAX_PATH - (Slash ? (Slash + 1 - IniPath) : 0), L"madapps.ini");
    LoadApps();

    InitCommonControlsEx(&icc);
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.hCursor = LoadCursorW(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_BTNFACE + 1);
    wc.hIcon = LoadIconW(hInstance, MAKEINTRESOURCEW(1));
    wc.lpszClassName = L"MadOSWelcome";
    RegisterClassExW(&wc);

    AdjustWindowRect(&rc, WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX, FALSE);
    hwnd = CreateWindowW(wc.lpszClassName, T(L"Bienvenue dans MadOS", L"Welcome to MadOS"),
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
