#!/usr/bin/env bash
set -euo pipefail

RUST_LLD="/home/deck/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/lib/rustlib/x86_64-unknown-linux-gnu/bin/rust-lld"

is_shared=0
args=()
for a in "$@"; do
    case "$a" in
        -m64|-nodefaultlibs|-B*|-fuse-ld=*)
            # GCC driver-only flags not understood by ld.lld
            ;;
        -Wl,*)
            IFS=',' read -r -a wl_parts <<< "${a#-Wl,}"
            for p in "${wl_parts[@]}"; do
                args+=("$p")
            done
            ;;
        -shared)
            is_shared=1
            args+=("$a")
            ;;
        -lgcc_s)
            args+=("/usr/lib/libgcc_s.so.1")
            ;;
        -lutil)
            args+=("/usr/lib/libutil.so.1")
            ;;
        -lrt)
            args+=("/usr/lib/librt.so.1")
            ;;
        -lpthread)
            args+=("/usr/lib/libpthread.so.0")
            ;;
        -ldl)
            args+=("/usr/lib/libdl.so.2")
            ;;
        *)
            args+=("$a")
            ;;
    esac
done

if [ "$is_shared" -eq 1 ]; then
    exec "$RUST_LLD" -flavor gnu -L/usr/lib /usr/lib/crti.o "${args[@]}" /usr/lib/crtn.o
else
    exec "$RUST_LLD" -flavor gnu -dynamic-linker /lib64/ld-linux-x86-64.so.2 -L/usr/lib /usr/lib/Scrt1.o /usr/lib/crti.o "${args[@]}" /usr/lib/crtn.o
fi
