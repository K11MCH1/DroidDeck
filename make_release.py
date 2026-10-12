#!/usr/bin/env python3
"""Packages one driver for its own release: the Linux half built here, the author's Android half
(when one exists) and the pair zip in DroidDeck's driver-bundle layout, plus the release notes.
Usage: make_release.py <driver-id> <linux-zip> <out-dir> <run-url> [android-zip built here]"""
import json, os, re, shutil, subprocess, sys, tempfile, zipfile, datetime

did, linux_zip, out_dir, run_url = sys.argv[1:5]
local_android = sys.argv[5] if len(sys.argv) > 5 and os.path.exists(sys.argv[5]) else None
d = next(x for x in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "drivers.json"))) if x["id"] == did)
os.makedirs(out_dir, exist_ok=True)

def fetch_android(spec, dest):
    """Newest release (pre-releases included) of spec['repo'] with an asset matching spec['asset']."""
    rels = json.loads(subprocess.check_output(["gh", "api", f"repos/{spec['repo']}/releases?per_page=10"], text=True))
    for rel in rels:
        for a in rel["assets"]:
            if re.search(spec["asset"], a["name"]):
                subprocess.check_call(["gh", "release", "download", rel["tag_name"], "-R", spec["repo"],
                                       "-p", a["name"], "-D", dest, "--clobber"])
                return os.path.join(dest, a["name"]), rel["tag_name"]
    return None, None

lmeta = json.load(zipfile.ZipFile(linux_zip).open("meta.json"))
shutil.copy(linux_zip, os.path.join(out_dir, f"{did}-Linux.zip"))
android_tag = None
built_here = False
path = None
if local_android:
    path, android_tag, built_here = local_android, "built here from the same source", True
elif d.get("android"):
    tmp = tempfile.mkdtemp()
    path, android_tag = fetch_android(d["android"], tmp)
if path:
    shutil.copy(path, os.path.join(out_dir, f"{did}-Android.zip"))
    with zipfile.ZipFile(os.path.join(out_dir, f"{did}-Pair.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps({
            "package": d["title"],
            "version": f"android {android_tag} + linux {lmeta['sourceCommit'][:12]}",
            "tag": did,
            "drivers": {"android": {"path": "android"}, "linux": {"path": "linux"}},
        }, indent=2))
        for src, prefix in ((path, "android/"), (linux_zip, "linux/")):
            with zipfile.ZipFile(src) as zin:
                for n in zin.namelist():
                    if not n.endswith("/"):
                        z.writestr(prefix + n, zin.read(n))

today = datetime.date.today().isoformat()
android_line = (f"- **Android half** (`{did}-Android.zip`): built here from the same source as the Linux half (the author has no Android release). It draws DroidDeck's screen (display slot)."
                if built_here else
                f"- **Android half** (`{did}-Android.zip`): the author's official release **{android_tag}**, unchanged. It draws DroidDeck's screen (display slot)."
                if android_tag else "- **Android half:** not available yet (the author has no Android release); it will be built here.")
pair_line = (f"- **Pair** (`{did}-Pair.zip`): both halves in one zip, in DroidDeck's driver-bundle layout."
             if android_tag else "- **Pair:** comes when the Android half is ready.")
notes = f"""# {d['title']} for DroidDeck (test)

Experimental. **Not tested on a device yet.** This release is replaced in place every time the driver is rebuilt.

## Which phones
{d['gpus']}

## Files
- **Linux half** (`{did}-Linux.zip`): runs inside DroidDeck's Linux for Steam and games (runtime slot). Built here from the author's public source.
{android_line}
{pair_line}

## This build
- Date: {today}
- Linux half source: [{d['build']['src_repo']}]({d['source']}) @ `{lmeta['sourceCommit']}`
- Minimum glibc: {lmeta.get('minGlibc', '?')}
- CI run: {run_url}
{f"- Note: {d['note']}" if d.get('note') else ""}

## Testing
DroidDeck does not load non-Adreno drivers yet; that comes in a DroidDeck test build. Until then the Linux half can be tried by hand in DroidDeck's desktop terminal. Report results with logs in the DroidDeck Discord testing thread.

## Credits
Driver by [{d['author']}]({d['source']}), built on [Mesa](https://gitlab.freedesktop.org/mesa/mesa) (MIT). This repo only rebuilds the source for DroidDeck's Linux and repackages the Android release as a pair.
"""
open(os.path.join(out_dir, "NOTES.md"), "w").write(notes)
print(notes)
