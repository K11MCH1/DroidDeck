#!/usr/bin/env python3
"""Builds the pair zips for every driver whose Linux build is present, and writes the release
notes from what the release will hold. Usage: make_release.py <linux-zips-dir> <out-dir> <existing-assets.txt>"""
import json, os, re, shutil, subprocess, sys, zipfile, tempfile

linux_dir, out_dir, existing_file = sys.argv[1:4]
drivers = json.load(open(os.path.join(os.path.dirname(__file__), "drivers.json")))
existing = set(open(existing_file).read().split()) if os.path.exists(existing_file) else set()
os.makedirs(out_dir, exist_ok=True)

def gh_json(*args):
    return json.loads(subprocess.check_output(["gh", *args], text=True))

def fetch_android(spec, dest):
    """Newest release (pre-releases included) of spec['repo'] with an asset matching spec['asset']."""
    rels = gh_json("api", f"repos/{spec['repo']}/releases?per_page=10")
    for rel in rels:
        for a in rel["assets"]:
            if re.search(spec["asset"], a["name"]):
                path = os.path.join(dest, a["name"])
                subprocess.check_call(["gh", "release", "download", rel["tag_name"], "-R", spec["repo"],
                                       "-p", a["name"], "-D", dest, "--clobber"])
                return path, rel["tag_name"]
    return None, None

rows, status = [], {}
for d in drivers:
    did = d["id"]
    linux_zip = os.path.join(linux_dir, f"{did}-Linux.zip")
    have_linux_new = os.path.exists(linux_zip)
    android_tag = None
    if have_linux_new:
        shutil.copy(linux_zip, os.path.join(out_dir, f"{did}-Linux.zip"))
        if d.get("android"):
            with tempfile.TemporaryDirectory() as t:
                path, android_tag = fetch_android(d["android"], t)
                if path:
                    shutil.copy(path, os.path.join(out_dir, f"{did}-Android.zip"))
                    pair = os.path.join(out_dir, f"{did}-Pair.zip")
                    lmeta = json.load(zipfile.ZipFile(linux_zip).open("meta.json"))
                    with zipfile.ZipFile(pair, "w", zipfile.ZIP_DEFLATED) as z:
                        z.writestr("manifest.json", json.dumps({
                            "package": d["title"], "version": f"android {android_tag} + linux {lmeta.get('sourceCommit','')[:12]}",
                            "tag": did,
                            "drivers": {"android": {"path": "android"}, "linux": {"path": "linux"}},
                        }, indent=2))
                        for src, prefix in ((path, "android/"), (linux_zip, "linux/")):
                            with zipfile.ZipFile(src) as zin:
                                for n in zin.namelist():
                                    if not n.endswith("/"):
                                        z.writestr(prefix + n, zin.read(n))
    names = {f"{did}-Linux.zip", f"{did}-Android.zip", f"{did}-Pair.zip"}
    present = {n for n in names if os.path.exists(os.path.join(out_dir, n)) or n in existing}
    if f"{did}-Pair.zip" in present:
        st = "✅ Pair ready"
    elif f"{did}-Linux.zip" in present:
        st = "🟡 Linux half ready, Android half pending"
    else:
        st = "🔧 Still building"
    status[did] = st
    rows.append(f"| **{d['title']}** | {d['gpus']} | {st} | [{d['author']}]({d['source']}) |")

notes = [
    "# DroidDeck drivers for Mali and Samsung Xclipse (test)",
    "",
    "Experimental Vulkan drivers so DroidDeck can run on phones without a Snapdragon (Adreno) GPU. "
    "**Not tested on a device yet.** This release is updated as each driver finishes building.",
    "",
    "Each driver comes as a pair, like DroidDeck's Adreno drivers:",
    "- **Android half** (`-Android.zip`): draws DroidDeck's screen (the display slot). This is the author's official Android release, unchanged.",
    "- **Linux half** (`-Linux.zip`): runs inside DroidDeck's Linux for Steam and games (the runtime slot). Built here from the author's public source.",
    "- **Pair** (`-Pair.zip`): both halves in one zip, in DroidDeck's driver-bundle layout.",
    "",
    "| Driver | GPUs, chips and devices | Status | Author |",
    "|---|---|---|---|",
    *rows,
    "",
    "## Notes",
    *[f"- **{d['title']}:** {d['note']}" for d in drivers if d.get("note")],
    "- DroidDeck itself does not load these yet: it only knows Adreno drivers today. The next DroidDeck test build adds that. "
    "Until then, testers can try the Linux half by hand in DroidDeck's desktop terminal (instructions in the testing thread).",
    "- Your phone's GPU decides which one to use: check it in Vulkan Caps Viewer or your phone's spec sheet.",
    "",
    "## Credits",
    "All driver work belongs to the authors above and to the Mesa project (MIT). This repo only rebuilds their source for "
    "DroidDeck's Linux and repackages their Android releases as pairs.",
]
open(os.path.join(out_dir, "NOTES.md"), "w").write("\n".join(notes) + "\n")
print("\n".join(rows))
