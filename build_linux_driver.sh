#!/usr/bin/env bash
# Builds a glibc (desktop Linux) Vulkan ICD from an Android-targeted Mesa fork, for DroidDeck's
# Linux runtime (Arch Linux ARM rootfs under PRoot on Android).
#   DRIVER=radv   JimVulkan/radv-xclipse                  (Samsung Xclipse, sgpu kernel driver)
#   DRIVER=panvk  FristOneRR-Admin/FristOneRR-Panvk-Source (Mali, Arm kbase kernel driver)
# SRC_REPO / SRC_REF pick the source; the output is linux_workdir/<ZIP_NAME>.
set -eo pipefail
green='\033[0;32m'; red='\033[0;31m'; nocolor='\033[0m'
die(){ echo -e "${red}[${DRIVER:-?}] $*${nocolor}" >&2; exit 1; }
log(){ echo -e "${green}[${DRIVER:-?}]${nocolor} $*"; }

repo="$(cd "$(dirname "$0")" && pwd)"
workdir="$(pwd)/linux_workdir"
sysroot="$workdir/sysroot"
mesa="$workdir/src"
stage="$workdir/stage"
hosttools="$workdir/host"
mirror="http://mirror.archlinuxarm.org/aarch64"
sysroot_seeds="glibc linux-api-headers libdrm wayland wayland-protocols libxcb libx11 libxshmfence
  libxext libxfixes libxrandr zlib zstd expat gcc-libs"
wl_version="1.26.0"
wl_sha256="64176eaa46e4969903e286f8e5ef8331affc17fdf03ac9b58381d2b23162b7a3"

case "$DRIVER" in
	radv)  lib=libvulkan_radeon.so;   icd=radeon_icd.aarch64.json ;;
	panvk) lib=libvulkan_panfrost.so; icd=panfrost_icd.aarch64.json ;;
	*) die "DRIVER must be radv or panvk" ;;
esac
[ -n "$SRC_REPO" ] && [ -n "$SRC_REF" ] && [ -n "$ZIP_NAME" ] || die "SRC_REPO, SRC_REF and ZIP_NAME are required"

fetch(){	# <url> <out>
	curl -fsSL --retry 6 --retry-delay 10 --retry-all-errors "$1" -o "$2" || die "download failed: $1"
}

build_sysroot(){
	mkdir -p "$workdir/db" "$workdir/pkgs" && cd "$workdir"
	log "fetching Arch Linux ARM package databases"
	local repo_name
	for repo_name in core extra alarm; do
		fetch "$mirror/$repo_name/$repo_name.db" "db/$repo_name.db"
		rm -rf "db/x_$repo_name" && mkdir -p "db/x_$repo_name"
		tar -xzf "db/$repo_name.db" -C "db/x_$repo_name" || die "$repo_name.db is not a package database"
	done

	# %DEPENDS% lives in a separate `depends` file and several names are virtual (%PROVIDES%).
	python3 - $sysroot_seeds > pkglist.txt <<'PY' || die "package closure failed"
import os, sys, collections
pkgs, provides = {}, collections.defaultdict(list)
def strip(d):
    for op in (">=", "<=", "==", ">", "<", "="):
        if op in d: return d.split(op)[0]
    return d
for repo in ("core", "extra", "alarm"):
    base = os.path.join("db", "x_" + repo)
    for entry in os.listdir(base):
        fields, key = {}, None
        for name in ("desc", "depends"):
            path = os.path.join(base, entry, name)
            if not os.path.exists(path): continue
            for line in open(path, encoding="utf-8", errors="replace"):
                line = line.rstrip("\n")
                if line.startswith("%") and line.endswith("%"): key = line.strip("%"); fields[key] = []
                elif line == "": key = None
                elif key: fields[key].append(line)
        n = fields.get("NAME", [None])[0]
        if not n: continue
        pkgs[n] = {"repo": repo, "file": fields["FILENAME"][0],
                   "depends": [strip(d) for d in fields.get("DEPENDS", [])],
                   "provides": [strip(p) for p in fields.get("PROVIDES", [])]}
        provides[n].append(n)
        for p in pkgs[n]["provides"]: provides[p].append(n)
seen, queue, missing = set(), list(sys.argv[1:]), []
while queue:
    want = queue.pop()
    real = want if want in pkgs else (provides.get(want) or [None])[0]
    if real is None: missing.append(want); continue
    if real in seen: continue
    seen.add(real)
    queue.extend(pkgs[real]["depends"])
if missing: sys.exit("unresolved: " + " ".join(missing))
for n in sorted(seen): print(pkgs[n]["repo"] + "/" + pkgs[n]["file"])
PY
	log "$(wc -l < pkglist.txt) packages in the sysroot closure"

	rm -rf "$sysroot" && mkdir -p "$sysroot"
	: > "$workdir/sysroot-packages.txt"
	local entry file
	while read -r entry; do
		file="${entry#*/}"
		# A mirror error page is not a package; check before extracting, not after.
		if ! tar -tf "pkgs/$file" >/dev/null 2>&1; then
			rm -f "pkgs/$file"
			fetch "$mirror/$entry" "pkgs/$file"
			tar -tf "pkgs/$file" >/dev/null || die "$file is not a package"
		fi
		tar -xf "pkgs/$file" -C "$sysroot" --no-same-owner --no-same-permissions \
			--exclude=.PKGINFO --exclude=.MTREE --exclude=.INSTALL --exclude=.BUILDINFO --exclude=.CHANGELOG \
			|| die "cannot unpack $file"
		echo "$file" >> "$workdir/sysroot-packages.txt"
	done < pkglist.txt
	chmod -R u+rwX "$sysroot"

	# glibc pulls in `filesystem`, so /lib -> /usr/lib is there and the linker script inside
	# libc.so (which names absolute /usr/lib paths, resolved against --sysroot) works. Assert what
	# the build actually opens rather than trust the closure: a mirror that moved a library into
	# another package would otherwise fail 20 minutes later inside meson.
	for f in usr/lib/libc.so.6 usr/lib/libdrm.so usr/lib/libwayland-client.so usr/lib/libxcb.so \
	         usr/lib/pkgconfig/libdrm.pc usr/lib/pkgconfig/wayland-client.pc usr/lib/pkgconfig/xcb.pc \
	         usr/share/pkgconfig/wayland-protocols.pc usr/include/xf86drm.h; do
		[ -e "$sysroot/$f" ] || die "sysroot is missing $f"
	done
	log "sysroot glibc: $(basename "$(readlink -f "$sysroot/usr/lib/libc.so.6")")"
}

# --- host wayland-scanner, built from the pinned release (seconds; no libraries, no docs) ---
build_host_scanner(){
	cd "$workdir"
	fetch "https://gitlab.freedesktop.org/wayland/wayland/-/releases/$wl_version/downloads/wayland-$wl_version.tar.xz" "wayland-$wl_version.tar.xz"
	echo "$wl_sha256  wayland-$wl_version.tar.xz" | sha256sum -c --quiet || die "wayland-$wl_version.tar.xz checksum mismatch"
	rm -rf "wayland-$wl_version" wayland-build && tar -xJf "wayland-$wl_version.tar.xz"
	meson setup wayland-build "wayland-$wl_version" --prefix "$hosttools" --libdir lib --buildtype release \
		-Dlibraries=false -Dscanner=true -Dtests=false -Ddocumentation=false -Ddtd_validation=false \
		|| die "host wayland-scanner: meson setup failed"
	ninja -C wayland-build install || die "host wayland-scanner: build failed"
	[ -x "$hosttools/bin/wayland-scanner" ] || die "host wayland-scanner was not installed"
	"$hosttools/bin/wayland-scanner" --version
}

fetch_src(){
	if [ "${SRC_KIND:-git}" = patchset ]; then fetch_patchset; return; fi
	rm -rf "$mesa"
	git init -q "$mesa"
	git -C "$mesa" remote add origin "https://github.com/$SRC_REPO.git"
	git -C "$mesa" fetch -q --depth=1 origin "$SRC_REF" || die "could not fetch $SRC_REPO $SRC_REF"
	git -C "$mesa" checkout -q FETCH_HEAD
	SRC_COMMIT="$(git -C "$mesa" rev-parse HEAD)"
	# Some forks link Android's liblog into everything; there is no liblog on desktop Linux.
	if grep -q "^  '-llog',$" "$mesa/meson.build"; then
		python3 - "$mesa/meson.build" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
old = "add_project_link_arguments(\n  '-llog',\n  language : ['c', 'cpp'],\n)\n"
assert old in s, "unexpected -llog block"
open(p, "w").write(s.replace(old, "", 1))
PY
		log "removed the fork's unconditional -llog"
	fi
	log "source $SRC_REPO @ $SRC_COMMIT ($(git -C "$mesa" log -1 --format=%cs))"
	restore_desktop_dirs
	# RADV Xclipse: its own __ANDROID__ blocks under src/amd only hold logging, debug properties and
	# CPU timing, which compat/ provides on glibc. Its non-Android branches were never built, so keep
	# the tested (Android) side. Mesa's DETECT_OS_ANDROID (gralloc, AHB) is left alone.
	if [ "$DRIVER" = radv ]; then
		local n
		local dirs=("$mesa/src/amd" "$mesa"/src/util/u_xclipse_prof.*)
		n="$(grep -rlE '#if(def)? *(defined\()?__ANDROID__' "${dirs[@]}" | wc -l)"
		grep -rlE '#if(def)? *(defined\()?__ANDROID__' "${dirs[@]}" | xargs -r sed -i -E \
			-e 's/^#ifdef __ANDROID__/#if 1 \/* glibc build: compat\/ *\//' \
			-e 's/^#if defined\(__ANDROID__\)/#if 1/'
		log "kept the Android-side diagnostics in $n src/amd + profiler files (compat/ on glibc)"
	fi
}

# A patch-series project (e.g. GunaCharanTeja/panvk-kbase-android): it pins upstream Mesa in
# sources.lock and applies its series for one GPU profile with its own scripts.
fetch_patchset(){
	[ -n "$PROFILE" ] || die "PROFILE is required for SRC_KIND=patchset"
	local prep="$workdir/prep"
	rm -rf "$prep" "$mesa"
	git init -q "$prep"
	git -C "$prep" remote add origin "https://github.com/$SRC_REPO.git"
	git -C "$prep" fetch -q --depth=1 origin "$SRC_REF" || die "could not fetch $SRC_REPO $SRC_REF"
	git -C "$prep" checkout -q FETCH_HEAD
	SRC_COMMIT="$(git -C "$prep" rev-parse HEAD)"
	(cd "$prep" && ./scripts/fetch-mesa.sh "$prep/work") || die "fetch-mesa.sh failed"
	(cd "$prep" && ./scripts/apply-patches.sh --profile "$PROFILE" --mesa "$prep/work/mesa") || die "apply-patches.sh failed for $PROFILE"
	mv "$prep/work/mesa" "$mesa"
	SRC_COMMIT="$SRC_COMMIT (profile $PROFILE, Mesa $(git -C "$mesa" rev-parse --short HEAD))"
	log "source $SRC_REPO @ $SRC_COMMIT"
}

# Android-only forks drop the parts of Mesa that only desktop Linux uses (the window-system
# loader, X11 helpers). Put back any that are missing, from upstream Mesa at MESA_OVERLAY_REF.
restore_desktop_dirs(){
	local missing=() d
	for d in src/loader src/x11; do
		[ -d "$mesa/$d" ] || missing+=("$d")
	done
	[ -d "$mesa/include/pci_ids" ] || missing+=(include/pci_ids)
	local need_uapi=0
	[ -f "$mesa/include/drm-uapi/nouveau_drm.h" ] || need_uapi=1
	[ -f "$mesa/include/vulkan/vulkan_wayland.h" ] || need_uapi=1
	[ ${#missing[@]} = 0 ] && [ $need_uapi = 0 ] && return 0
	local ref="${MESA_OVERLAY_REF:-main}" up="$workdir/mesa-upstream"
	log "restoring ${missing[*]} from upstream Mesa $ref"
	rm -rf "$up" && git init -q "$up"
	git -C "$up" remote add origin https://gitlab.freedesktop.org/mesa/mesa.git
	git -C "$up" fetch -q --depth=1 origin "$ref" || die "could not fetch upstream Mesa $ref"
	git -C "$up" checkout -q FETCH_HEAD
	for d in "${missing[@]}"; do
		[ -d "$up/$d" ] || die "upstream Mesa has no $d"
		cp -r "$up/$d" "$mesa/$d"
	done
	if [ $need_uapi = 1 ] || [ ! -f "$mesa/include/vulkan/vulkan_wayland.h" ]; then
		local before after
		before="$(cd "$mesa/include" && git ls-files --others --cached . | wc -l)"
		cp -rn "$up/include/." "$mesa/include/"
		after="$(cd "$mesa/include" && ls -R . | grep -c '\.h$')"
		log "added the fork's missing include/ headers from upstream (fork's own kept)"
	fi
	OVERLAY_COMMIT="$(git -C "$up" rev-parse HEAD)"
	log "restored from upstream Mesa $OVERLAY_COMMIT"
}

# PanVK compiles OpenCL kernels at build time: mesa_clc, vtn_bindgen2 and panfrost_compile must
# run on this x86 machine, so build them natively first and hand them to the cross build.
build_panvk_host_tools(){
	cd "$mesa"
	rm -rf build-host
	# clang: Mesa's SPIRV-Tools probe passes clang-only warning flags, which gcc rejects.
	CC=clang-18 CXX=clang++-18 meson setup build-host --prefix "$hosttools" --libdir lib --buildtype release \
		-Dvulkan-drivers=panfrost -Dgallium-drivers= -Dplatforms= -Dopengl=false \
		-Dgbm=disabled -Dglx=disabled -Degl=disabled -Dvulkan-layers= -Dtools= -Dxmlconfig=disabled \
		-Dllvm=enabled -Dmesa-clc=enabled -Dinstall-mesa-clc=true \
		-Dprecomp-compiler=enabled -Dinstall-precomp-compiler=true -Dpanfrost-kmds=kbase \
		|| { tail -80 build-host/meson-logs/meson-log.txt; die "host tools: meson setup failed"; }
	# Only the three build tools are needed from this machine's build, not the driver itself.
	local t target
	for t in mesa_clc vtn_bindgen2 panfrost_compile; do
		target="$(ninja -C build-host -t targets all | grep -oE "^src/[^: ]*/$t:" | grep -v '\.p/' | sed 's/:$//' | head -1)"
		[ -n "$target" ] || die "host tools: no target for $t"
		ninja -C build-host "$target" || die "host tools: $t failed to build"
		install -Dm755 "build-host/$target" "$hosttools/bin/$t"
	done
	ls -l "$hosttools/bin"
}

# DroidDeck-side fixes every PanVK build needs, whatever the fork.
apply_panvk_fixes(){
	[ "$DRIVER" = panvk ] || return 0
	python3 "$repo/patches/panvk_kbase_drm_node.py" "$mesa" || die "panvk_kbase_drm_node.py failed"
	grep -q BL_DRM_STANDIN "$mesa/src/panfrost/vulkan/panvk_physical_device.c" || die "DRM-node fix did not land"
}

build(){
	cd "$mesa"
	local cross="$workdir/cross.ini" native="$workdir/native.ini"
	cat > "$cross" <<EOC
[binaries]
c = 'aarch64-linux-gnu-gcc'
cpp = 'aarch64-linux-gnu-g++'
ar = 'aarch64-linux-gnu-ar'
strip = 'aarch64-linux-gnu-strip'
pkg-config = 'pkg-config'
[properties]
sys_root = '$sysroot'
pkg_config_libdir = '$sysroot/usr/lib/pkgconfig:$sysroot/usr/share/pkgconfig'
[built-in options]
c_args = ['--sysroot=$sysroot']
cpp_args = ['--sysroot=$sysroot']
c_link_args = ['--sysroot=$sysroot', '-L$sysroot/usr/lib']
cpp_link_args = ['--sysroot=$sysroot', '-L$sysroot/usr/lib']
[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
EOC
	cat > "$native" <<EOC
[binaries]
c = 'gcc'
cpp = 'g++'
pkg-config = '/usr/bin/pkg-config'
cmake = '/usr/bin/cmake'
wayland-scanner = '$hosttools/bin/wayland-scanner'
glslangValidator = '$(command -v glslangValidator)'
[built-in options]
pkg_config_path = '$hosttools/lib/pkgconfig'
EOC
	local extra=()
	if [ "$DRIVER" = radv ]; then
		# The fork patches libdrm (subprojects/packagefiles) for Samsung's sgpu kernel driver, so its
		# own static libdrm is used, exactly as its Android build does, never the sysroot's.
		# Some files call the Android log/property functions without including their headers.
		compat_inc="-include $repo/compat/android/log.h -include $repo/compat/sys/system_properties.h"
		extra=(-Dvulkan-drivers=amd -Dllvm=disabled
		       -Dallow-fallback-for=libdrm --force-fallback-for=libdrm
		       -Dlibdrm:default_library=static)
	else
		# The host tools belong in [binaries], before the [built-in options] section.
		local t
		for t in panfrost_compile vtn_bindgen2 mesa_clc; do
			sed -i "/^\[binaries\]/a $t = '$hosttools/bin/$t'" "$native"
		done
		export PATH="$hosttools/bin:$PATH"
		extra=(-Dvulkan-drivers=panfrost -Dpanfrost-kmds=${PANFROST_KMDS:-kbase,panfrost} -Dllvm=disabled
		       -Dmesa-clc=system -Dprecomp-compiler=system)
	fi
	rm -rf build-linux
	meson setup build-linux --cross-file "$cross" --native-file "$native" \
		--prefix /usr --libdir lib --buildtype release -Db_ndebug=true \
		-Dgallium-drivers= -Dplatforms=wayland,x11 -Dopengl=false \
		-Dgbm=disabled -Dglx=disabled -Degl=disabled -Dvulkan-layers= -Dtools= \
		-Dxmlconfig=disabled -Dperfetto=false -Dlmsensors=disabled \
		-Dc_args="-I$repo/compat ${compat_inc:-}" -Dcpp_args="-I$repo/compat ${compat_inc:-}" \
		"${extra[@]}" \
		|| { echo "== meson log =="; tail -120 build-linux/meson-logs/meson-log.txt 2>/dev/null; die "meson setup failed"; }
	local target
	target="$(ninja -C build-linux -t targets all | grep -oE "^src/[^: ]*/$lib:" | grep -v '\.p/' | sed 's/:$//' | head -1)"
	[ -n "$target" ] || die "no ninja target for $lib"
	log "building $target"
	ninja -C build-linux "$target" || die "build failed"
	built="build-linux/$target"
}

package(){
	cd "$mesa"
	rm -rf "$stage" && mkdir -p "$stage"
	aarch64-linux-gnu-strip -o "$stage/$lib" "$built" || die "strip failed"
	local needed glibc_min vk
	needed="$(aarch64-linux-gnu-readelf -d "$stage/$lib" | awk '/NEEDED/{print $5}' | tr -d '[]' | tr '\n' ' ')"
	log "NEEDED: $needed"
	echo " $needed " | grep -q ' libc.so.6 ' || die "not a glibc build (no libc.so.6)"
	if echo " $needed " | grep -qE ' (liblog|libnativewindow|libhardware|libc)\.so '; then
		die "still links Android libraries: $needed"
	fi
	glibc_min="$(aarch64-linux-gnu-readelf -V -W "$stage/$lib" | grep -oP 'GLIBC_\K[0-9]+\.[0-9]+(\.[0-9]+)?' | sort -uV | tail -1)"
	log "minimum glibc: $glibc_min"
	vk="$(grep '^#define VK_HEADER_VERSION ' include/vulkan/vulkan_core.h | awk '{print $3}')"
	cat > "$stage/$icd" <<EOJ
{
    "ICD": {
        "api_version": "1.4.$vk",
        "library_path": "./$lib"
    },
    "file_format_version": "1.0.1"
}
EOJ
	cat > "$stage/meta.json" <<EOJ
{
  "name": "$META_NAME",
  "driver": "$DRIVER",
  "libraryName": "$lib",
  "icd": "$icd",
  "libc": "glibc",
  "minGlibc": "$glibc_min",
  "source": "https://github.com/$SRC_REPO",
  "sourceCommit": "$SRC_COMMIT",
  "upstreamOverlay": "${OVERLAY_COMMIT:-none}",
  "description": "glibc build for DroidDeck's Linux runtime. Not for Winlator or Bannerlator: use the original Android release there."
}
EOJ
	cp "$mesa/LICENSE" "$stage/LICENSE" 2>/dev/null || cp "$mesa/docs/license.rst" "$stage/LICENSE" 2>/dev/null || true
	(cd "$stage" && zip -r9 "$workdir/$ZIP_NAME" .) >/dev/null
	sha256sum "$workdir/$ZIP_NAME" "$stage/$lib"
}

mkdir -p "$workdir"
build_sysroot
build_host_scanner
fetch_src
apply_panvk_fixes
if [ "$DRIVER" = panvk ]; then build_panvk_host_tools; fi
build
package
