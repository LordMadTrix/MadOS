# MadOS: reports are labelled "mados" so the LiberNT project can tell them
# apart, and the build never turns the optional data on: diagnostic data stays
# off until the user allows it (AllowTelemetry = 0 in hivesft.inf, changed
# from the System control panel).
set(DIAGDATA_CHANNEL "mados" CACHE STRING "Channel recorded in the diagnostic data reports, empty for the builds published to users")
set(DIAGDATA_OPTIONAL_DEFAULT "")
configure_file(diagdata_channel.inf.in ${CMAKE_CURRENT_BINARY_DIR}/diagdata_channel.inf @ONLY)

add_executable(diagdata diagdata.c diagdata.rc)
set_module_type(diagdata win32cui UNICODE)
add_importlibs(diagdata winhttp setupapi rpcrt4 advapi32 msvcrt kernel32 ntdll)
add_cd_file(TARGET diagdata DESTINATION reactos/system32 FOR all)
add_registry_inf(diagdata_reg.inf ${CMAKE_CURRENT_BINARY_DIR}/diagdata_channel.inf)
