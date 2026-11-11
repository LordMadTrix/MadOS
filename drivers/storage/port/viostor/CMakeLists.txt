# VirtIO block (viostor) : disque "virtio" de QEMU, KVM et Proxmox.
# Sources : https://github.com/virtio-win/kvm-guest-drivers-windows (BSD-3-Clause), voir SOURCE.txt.

# Copie a jour de la bibliotheque VirtIO officielle (celle de sdk/lib/drivers/virtio,
# utilisee par netkvm, est plus ancienne).
include_directories(BEFORE virtio)

list(APPEND SOURCE
    virtio_pci.c
    virtio_stor.c
    virtio_stor_hw_helper.c
    virtio_stor_utils.c
    virtio/VirtIOPCICommon.c
    virtio/VirtIOPCILegacy.c
    virtio/VirtIOPCIModern.c
    virtio/VirtIORing.c
    virtio/VirtIORing-Packed.c)

add_library(viostor MODULE ${SOURCE} viostor.rc)
set_module_type(viostor kernelmodedriver)
add_importlibs(viostor storport ntoskrnl hal)
add_cd_file(TARGET viostor DESTINATION reactos/system32/drivers NO_CAB FOR all)
add_driver_inf(viostor viostor.inf)

if(NOT MSVC)
    target_compile_options(viostor PRIVATE -Wno-unused-function -Wno-pointer-sign -Wno-unknown-pragmas
        -Wno-switch -Wno-unused-variable -include ${CMAKE_CURRENT_SOURCE_DIR}/viostor_compat.h)
endif()
if(CMAKE_C_COMPILER_ID STREQUAL "Clang")
    target_compile_options(viostor PRIVATE -Wno-pragma-pack -Wno-unused-but-set-variable -Wno-microsoft-anon-tag
        -Wno-extra-tokens -Wno-constant-conversion
        -Wno-incompatible-function-pointer-types -Wno-unused-value)
endif()
