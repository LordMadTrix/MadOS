# MadOS - "Bienvenue dans MadOS" : choix des applications a installer
add_executable(madwelcome madwelcome.c madwelcome.rc)
set_module_type(madwelcome win32gui UNICODE)
add_importlibs(madwelcome urlmon wintrust crypt32 bcrypt shlwapi comctl32 user32 gdi32 advapi32 msvcrt kernel32 ntdll)
add_cd_file(TARGET madwelcome DESTINATION reactos/system32 FOR all)
add_cd_file(FILE ${CMAKE_CURRENT_SOURCE_DIR}/madapps.ini DESTINATION reactos/system32 FOR all)
