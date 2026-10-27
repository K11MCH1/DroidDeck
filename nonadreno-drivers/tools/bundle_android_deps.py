#!/usr/bin/env python3
"""Makes an Android (bionic) driver half self-contained: every library its driver NEEDs that is
not an Android system library is shipped beside it, and a NEEDED libdrm.so is pointed at our own
libdrm_full.so, because the vendor libdrm.so (already loaded, same SONAME, no
drmCloseBufferHandle) shadows any libdrm.so in the driver folder and adrenotools then silently
falls back to the vendor driver. Finding by ryanistr (https://github.com/ryanistr/DroidDeck-Mali,
docs/development/panvk-mali-g77-bringup.md section 16).

Only the dynamic section of a NEEDED libdrm.so entry is changed (patchelf --replace-needed); the
driver's code is never touched. Fails when a NEEDED library can be found neither on Android nor in
<deps-dir> (built by tools/build_android_deps.sh).

Usage: bundle_android_deps.py <android-zip> <deps-dir>     (rewrites the zip in place)"""
import json, os, shutil, subprocess, sys, tempfile, zipfile

# Present on every Android 10+ device, in the app's or the sphal/default namespace.
SYSTEM = {"libc.so", "libm.so", "libdl.so", "liblog.so", "libnativewindow.so", "libsync.so",
          "libvndksupport.so", "libandroid.so", "libz.so", "libhardware.so", "libcutils.so",
          "libutils.so", "libEGL.so", "libGLESv2.so", "libvulkan.so"}
RENAME = {"libdrm.so": "libdrm_full.so"}

zpath, deps = sys.argv[1], sys.argv[2]
work = tempfile.mkdtemp()
with zipfile.ZipFile(zpath) as z:
    names = [n for n in z.namelist() if not n.endswith("/")]
    z.extractall(work)

def find(base):
    for n in names:
        if os.path.basename(n) == base:
            return os.path.join(work, n)
    return None

def needed(path):
    out = subprocess.check_output(["readelf", "-d", path], text=True)
    return [l.split("[", 1)[1].split("]", 1)[0] for l in out.splitlines() if "(NEEDED)" in l]

meta_path = find("meta.json")
lib = json.load(open(meta_path))["libraryName"] if meta_path else None
driver = find(lib) if lib else None
if not driver:
    sys.exit(f"{zpath}: driver library {lib!r} not found")
ddir = os.path.dirname(driver)
before = needed(driver)
print(f"before: {os.path.basename(driver)} NEEDED {' '.join(before)}")

changed = False
for old, new in RENAME.items():
    if old in before:
        subprocess.check_call(["patchelf", "--page-size", "16384", "--replace-needed", old, new, driver])
        changed = True
        print(f"  NEEDED {old} -> {new}")

added = []
todo = [driver]
seen = set()
while todo:
    cur = todo.pop()
    for n in needed(cur):
        if n in SYSTEM or n in seen:
            continue
        seen.add(n)
        here = os.path.join(ddir, n)
        if not os.path.exists(here):
            src = os.path.join(deps, n)
            if not os.path.isfile(src):
                sys.exit(f"{os.path.basename(cur)} needs {n}: not an Android system library and not in {deps}")
            shutil.copy(src, here)
            added.append(n)
            changed = True
        todo.append(here)

after = needed(driver)
print(f"after:  {os.path.basename(driver)} NEEDED {' '.join(after)}")
print(f"  shipped beside it: {' '.join(sorted(seen)) or 'nothing needed'}; added now: {' '.join(added) or 'none'}")

if changed:
    tmp = zpath + ".new"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(work):
            for f in sorted(files):
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, work))
    os.replace(tmp, zpath)
shutil.rmtree(work)
