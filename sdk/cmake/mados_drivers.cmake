# MadOS : pilotes locaux integres au disque preinstalle (VHD, image USB).
#
# MADOS_DRIVERS_DIR designe un dossier de paquets de pilotes (un .inf et ses
# fichiers par sous-dossier), garde HORS du depot. Son contenu est copie dans
# %SystemRoot%\MadOS\Pilotes et installe au premier demarrage par
#   pnputil /add-driver %SystemRoot%\MadOS\Pilotes\*.inf /subdirs /install
# (journal : %SystemRoot%\MadOS\Pilotes\installation.log).
#
# Sert a construire une image PERSONNELLE pour un PC donne. Une image qui
# contient des pilotes proprietaires (Intel, Realtek...) ne doit jamais etre
# publiee : leur licence n'autorise pas la redistribution.

set(MADOS_DRIVERS_DIR "" CACHE PATH
    "Dossier local de pilotes a integrer au disque preinstalle (image personnelle, a ne pas publier)")

if(MADOS_DRIVERS_DIR)
    get_filename_component(_mados_drivers_dir "${MADOS_DRIVERS_DIR}" ABSOLUTE)
    if(NOT IS_DIRECTORY "${_mados_drivers_dir}")
        message(FATAL_ERROR "MADOS_DRIVERS_DIR n'est pas un dossier : ${_mados_drivers_dir}")
    endif()

    file(GLOB_RECURSE _mados_driver_files LIST_DIRECTORIES false
        RELATIVE "${_mados_drivers_dir}" "${_mados_drivers_dir}/*")
    set(_mados_driver_infs 0)
    foreach(_mados_driver_file IN LISTS _mados_driver_files)
        if(_mados_driver_file MATCHES "[ =;]")
            message(FATAL_ERROR "MADOS_DRIVERS_DIR : renommer sans espace, '=' ni ';' : ${_mados_driver_file}")
        endif()
        if(_mados_driver_file MATCHES "\\.[iI][nN][fF]$")
            math(EXPR _mados_driver_infs "${_mados_driver_infs} + 1")
        endif()
        set_property(GLOBAL APPEND PROPERTY PREINSTALL_OVERLAY_FILE_LIST
            "reactos/MadOS/Pilotes/${_mados_driver_file}=${_mados_drivers_dir}/${_mados_driver_file}")
        list(APPEND _preinstall_overlay_deps "${_mados_drivers_dir}/${_mados_driver_file}")
    endforeach()
    if(_mados_driver_infs EQUAL 0)
        message(FATAL_ERROR "MADOS_DRIVERS_DIR ne contient aucun fichier .inf : ${_mados_drivers_dir}")
    endif()

    # Installation au premier demarrage (cmd developpe %SystemRoot%)
    set(_mados_drivers_inf "${CMAKE_CURRENT_BINARY_DIR}/mados_drivers.inf")
    file(WRITE "${_mados_drivers_inf}" "[Version]\nSignature = \"$Windows NT$\"\n\n[AddReg]\n\n"
        "HKLM,\"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce\",\"MadOSPilotes\",0x00000000,"
        "\"cmd.exe /c pnputil.exe /add-driver %SystemRoot%\\MadOS\\Pilotes\\*.inf /subdirs /install > %SystemRoot%\\MadOS\\Pilotes\\installation.log 2>&1\"\n")
    set_property(GLOBAL APPEND PROPERTY PREINSTALL_REGISTRY_INF_LIST "${_mados_drivers_inf}")

    list(LENGTH _mados_driver_files _mados_driver_count)
    message(STATUS "MadOS : ${_mados_driver_infs} pilote(s) local(aux) integre(s) (${_mados_driver_count} fichiers) - image personnelle, a ne pas publier")
endif()
