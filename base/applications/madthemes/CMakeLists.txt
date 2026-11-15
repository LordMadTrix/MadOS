# MadOS - "Themes" : appliquer un theme MadOS d'un clic
add_executable(madthemes madthemes.c madthemes.rc)
set_module_type(madthemes win32gui UNICODE)
add_importlibs(madthemes uxtheme shell32 user32 gdi32 advapi32 msvcrt kernel32)
add_cd_file(TARGET madthemes DESTINATION reactos/system32 FOR all)
