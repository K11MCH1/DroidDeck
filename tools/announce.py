#!/usr/bin/env python3
"""Posts a release to the DroidDeck "Crash on mali devices" thread as DroidDeck-Bot.

announce.py <tag> [message-file]
- With a message file, that text is posted (plain words, written for testers).
- Without one, the release's "## New in this build" section is posted.
The webhook comes from DISCORD_WEBHOOK; the thread id from DISCORD_THREAD_ID.
"""
import json, os, re, subprocess, sys, urllib.request

tag = sys.argv[1]
repo = os.environ.get("GITHUB_REPOSITORY", "The412Banner/droiddeck-nonadreno-drivers")
rel = json.loads(subprocess.check_output(
    ["gh", "release", "view", tag, "-R", repo, "--json", "name,body,url"]))
if len(sys.argv) > 2 and os.path.getsize(sys.argv[2]):
    text = open(sys.argv[2]).read().strip()
else:
    m = re.search(r"## New in this build[^\n]*\n(.*?)(?=\n## |\n<details>|\Z)", rel["body"], re.S)
    text = (m.group(1) if m else rel["body"]).strip()
text = re.sub(r"\*\*(.+?)\*\*", r"**\1**", text)  # Discord takes GitHub bold as is
if len(text) > 3800:
    text = text[:3800].rsplit("\n", 1)[0] + "\n…"
embed = {
    "title": rel["name"],
    "url": rel["url"],
    "description": text + f"\n\n**Download:** {rel['url']}\nSend logs with Setup → Share logs.",
    "color": 0x2B7FFF,
}
# MENTIONS: comma-separated Discord user ids to @ in the message text (mentions inside an embed never notify).
users = [u.strip() for u in os.environ.get("MENTIONS", "").split(",") if u.strip().isdigit()]
payload = {"username": "DroidDeck-Bot", "embeds": [embed], "allowed_mentions": {"parse": [], "users": users}}
if users:
    payload["content"] = " ".join(f"<@{u}>" for u in users)
body = json.dumps(payload).encode()
url = os.environ["DISCORD_WEBHOOK"] + f"?thread_id={os.environ['DISCORD_THREAD_ID']}&wait=true"
req = urllib.request.Request(url, data=body, method="POST",
                             headers={"Content-Type": "application/json", "User-Agent": "droiddeck-nonadreno-drivers"})
print("posted message", json.load(urllib.request.urlopen(req))["id"])
