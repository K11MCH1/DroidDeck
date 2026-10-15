#!/usr/bin/env python3
"""CSF PanVK: call the provoking-vertex helper with its full 64-bit GPU address.

get_fb_descs() (src/panfrost/vulkan/csf/panvk_vX_cmd_draw.c) kept the address of the
fn_set_fbds_provoking_vertex stream in a uint32_t before cs_call()ing it. On Android's kbase,
GPU addresses are SAME_VA and sit above 4 GB (fns_bo around 0x5f_fffef000), so the command
stream frontend prefetched from the truncated 0x00000000fffef000: a translation fault
(exception 0xc1) that stops every group -> queue timeouts, DEVICE_LOST, and a Zink client whose
memory grows until it is killed. The path is only taken when a render pass starts before the
provoking-vertex mode is known, which Chromium on Zink (the Steam client) does on every pass.
Upstream Mesa main already uses uint64_t here.

Based on the fix by emirvapur11 (https://github.com/emir34-34/DroidDeck/commit/8f18a5ad),
as ported by ryanistr (https://github.com/ryanistr/DroidDeck-Mali). The change itself is a
one-line Mesa (MIT) fix.

Idempotent: does nothing when the tree has no CSF backend or already uses a 64-bit address.
Usage: panvk_csf_provoking_vertex_u64.py <mesa-tree>"""
import pathlib, re, sys

p = pathlib.Path(sys.argv[1]) / "src/panfrost/vulkan/csf/panvk_vX_cmd_draw.c"
if not p.exists():
    print("no CSF backend in this tree: nothing to do"); sys.exit(0)
s = p.read_text()
pat = re.compile(r"\buint32_t(\s+fn_addr\s*=\s*\n?\s*dev->draw_ctx->fns_bo->addr\.dev)")
n = len(pat.findall(s))
if n == 0:
    if re.search(r"\buint64_t\s+fn_addr\s*=", s) or "fn_addr" not in s:
        print("fn_addr is already 64-bit (or absent): nothing to do"); sys.exit(0)
    sys.exit("fn_addr found in an unexpected form; check get_fb_descs() by hand")
p.write_text(pat.sub(r"uint64_t\1", s))
print(f"applied: provoking-vertex helper address widened to 64 bits ({n} site(s))")
