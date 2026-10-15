#!/usr/bin/env bash
# Builds the libraries an Android (bionic) driver half may need beside it, for arm64 Android 10+,
# with the runner's NDK: libdrm_full.so, libz.so.1, libzstd.so.1, libc++_shared.so.
#
# Why (measured by ryanistr on a MT6893, https://github.com/ryanistr/DroidDeck-Mali,
# docs/development/panvk-mali-g77-bringup.md section 16): adrenotools loads the driver in its own
# linker namespace with the driver folder as its library path, so a NEEDED library missing from
# that folder makes the hook fail and silently fall back to the vendor Mali driver. libdrm is
# worse: the vendor /vendor/lib64/libdrm.so is already loaded (gralloc), declares the same SONAME
# and lacks drmCloseBufferHandle, so it shadows any libdrm.so shipped beside the driver. Our full
# libdrm therefore gets its own SONAME, libdrm_full.so.
#
# Usage: build_android_deps.sh <out-dir>     (needs ANDROID_NDK_HOME or ANDROID_NDK_LATEST_HOME)
set -euo pipefail
out="$(mkdir -p "$1" && cd "$1" && pwd)"
ndk="${ANDROID_NDK_HOME:-${ANDROID_NDK_LATEST_HOME:?no NDK}}"
api=29
work="$(mktemp -d)"
tc="$ndk/build/cmake/android.toolchain.cmake"
bin="$ndk/toolchains/llvm/prebuilt/linux-x86_64/bin"

fetch(){	# <url> <sha256>
	local f="$work/$(basename "$1")"
	curl -fsSL --retry 5 --retry-delay 5 "$1" -o "$f"
	echo "$2  $f" | sha256sum -c --quiet
	tar -xf "$f" -C "$work"
}

# zlib (SONAME libz.so.1)
fetch https://github.com/madler/zlib/releases/download/v1.3.1/zlib-1.3.1.tar.gz \
	9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23
cmake -S "$work/zlib-1.3.1" -B "$work/zlib-build" -G Ninja -DCMAKE_TOOLCHAIN_FILE="$tc" \
	-DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-$api -DCMAKE_BUILD_TYPE=Release \
	-DZLIB_BUILD_EXAMPLES=OFF >/dev/null
ninja -C "$work/zlib-build" zlib >/dev/null
# The NDK toolchain builds unversioned sonames (libz.so would clash with Android's own zlib).
cp -L "$(find "$work/zlib-build" -maxdepth 1 -name 'libz.so*' -type f | head -1)" "$out/libz.so.1"
patchelf --set-soname libz.so.1 "$out/libz.so.1"

# zstd (SONAME libzstd.so.1)
fetch https://github.com/facebook/zstd/releases/download/v1.5.6/zstd-1.5.6.tar.gz \
	8c29e06cf42aacc1eafc4077ae2ec6c6fcb96a626157e0593d5e82a34fd403c1
cmake -S "$work/zstd-1.5.6/build/cmake" -B "$work/zstd-build" -G Ninja -DCMAKE_TOOLCHAIN_FILE="$tc" \
	-DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-$api -DCMAKE_BUILD_TYPE=Release \
	-DZSTD_BUILD_STATIC=OFF -DZSTD_BUILD_SHARED=ON -DZSTD_BUILD_PROGRAMS=OFF -DZSTD_BUILD_TESTS=OFF \
	-DZSTD_LEGACY_SUPPORT=OFF >/dev/null
ninja -C "$work/zstd-build" libzstd_shared >/dev/null
cp -L "$(find "$work/zstd-build" -name 'libzstd.so*' -type f | head -1)" "$out/libzstd.so.1"
patchelf --set-soname libzstd.so.1 "$out/libzstd.so.1"

# libdrm, core library only, renamed to libdrm_full.so
fetch https://dri.freedesktop.org/libdrm/libdrm-2.4.124.tar.xz \
	ac36293f61ca4aafaf4b16a2a7afff312aa4f5c37c9fbd797de9e3c0863ca379
cat > "$work/android.ini" <<EOC
[binaries]
c = '$bin/aarch64-linux-android$api-clang'
ar = '$bin/llvm-ar'
strip = '$bin/llvm-strip'
[host_machine]
system = 'android'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
EOC
d=""; for o in intel radeon amdgpu nouveau vmwgfx omap exynos freedreno tegra vc4 etnaviv; do d="$d -D$o=disabled"; done
meson setup "$work/drm-build" "$work/libdrm-2.4.124" --cross-file "$work/android.ini" --buildtype release \
	-Ddefault_library=shared $d -Dcairo-tests=disabled -Dman-pages=disabled -Dvalgrind=disabled \
	-Dtests=false -Dinstall-test-programs=false -Dudev=false >/dev/null
ninja -C "$work/drm-build" >/dev/null
cp -L "$(find "$work/drm-build" -maxdepth 1 -name 'libdrm.so*' -type f | head -1)" "$out/libdrm_full.so"
patchelf --set-soname libdrm_full.so "$out/libdrm_full.so"

# libc++_shared from the NDK, as is
cp "$ndk/toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/lib/aarch64-linux-android/libc++_shared.so" "$out/"

"$bin/llvm-strip" --strip-unneeded "$out"/libz.so.1 "$out"/libzstd.so.1 "$out"/libdrm_full.so
for f in "$out"/*; do
	echo "$(basename "$f"): SONAME $("$bin/llvm-readelf" -d "$f" | awk '/SONAME/{print $NF}') NEEDED $("$bin/llvm-readelf" -d "$f" | awk '/NEEDED/{print $NF}' | tr '\n' ' ')"
done
for f in libz.so.1 libzstd.so.1; do
	"$bin/llvm-readelf" -d "$out/$f" | grep -q "SONAME.*\[$f\]" || { echo "$f has the wrong SONAME" >&2; exit 1; }
done
"$bin/llvm-readelf" -d "$out/libdrm_full.so" | grep -q 'SONAME.*\[libdrm_full.so\]' || { echo "libdrm_full.so has the wrong SONAME" >&2; exit 1; }
"$bin/llvm-readelf" --dyn-syms -W "$out/libdrm_full.so" | grep -q ' drmCloseBufferHandle$' || { echo "libdrm_full.so lacks drmCloseBufferHandle" >&2; exit 1; }
(cd "$out" && sha256sum *)
rm -rf "$work"
