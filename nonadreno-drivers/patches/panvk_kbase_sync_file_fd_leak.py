#!/usr/bin/env python3
"""PanVK on kbase leaks one file descriptor per presented frame until the process hits its fd
limit ("MESA: failed to import sync file 'Too many open files'", then "kbase: failed to
duplicate dma-buf"), after which the GPU stalls; on a Mali-G925 Steam froze after ~10 minutes.

kbase_cpu_sync_import_sync_file() dup()s the sync_file into a heap "waiter" kept in
ks->pending_data, and kbase_sync_file_waiter_free() closes it. Places that drop the payload by
just setting pending_data to NULL (or overwriting it) lose the waiter, so the dup()'d fd and the
struct leak. In zenithblue's tree that is the CPU wait finishing (the WSI path: import a dma-buf's
sync_file, wait on it, destroy the sync — once per frame), signal, reset, re-arming with
panvk_kbase_sync_set_pending() and the destination of a move; wonderkast02's tree already frees
in all of those except signal.

This frees the sync-file waiter before every such drop that does not already do so (it only acts
when the payload is a sync-file waiter, so GPU-queue payloads are untouched). The moved-from side
of a move keeps its NULL assignment: its payload now belongs to the destination.

No-op (exit 0) on trees without this sync code (e.g. the JM fork).
Usage: panvk_kbase_sync_file_fd_leak.py <mesa-tree>"""
import pathlib, re, sys

tree = pathlib.Path(sys.argv[1])
p = tree / "src/panfrost/vulkan/panvk_physical_device.c"
s = p.read_text()
if "kbase_sync_file_wait_func" not in s:
    print("no kbase sync_file waiter in this tree: nothing to do"); sys.exit(0)
if "BL_SYNC_FILE_FD_LEAK" in s:
    print("already applied"); sys.exit(0)

lines = s.split("\n")

# Skip the body of kbase_sync_file_waiter_free() itself (it is the one place that may NULL it).
free_def = next((i for i, l in enumerate(lines)
                 if l.startswith("kbase_sync_file_waiter_free(") and not l.rstrip().endswith(";")),
                None)
if free_def is None:
    sys.exit("kbase_sync_file_waiter_free() definition not found")
free_end = next(i for i in range(free_def, len(lines)) if lines[i] == "}")
decl = next((i for i, l in enumerate(lines)
             if l.startswith("kbase_sync_file_waiter_free(") and l.rstrip().endswith(";")), free_def)

drop = re.compile(r"^(\s*)(ks|ks_dst)->pending_data = (NULL|data|ks_src->pending_data);")
fixed = []
out = []
for i, l in enumerate(lines):
    m = drop.match(l)
    if m and not (free_def <= i <= free_end):
        indent, var, val = m.groups()
        # Already freed just above (wonderkast02 has most of these)?
        if not any("kbase_sync_file_waiter_free(" in x for x in lines[max(0, i - 6):i]):
            if i < decl:  # kbase_cpu_sync_init(): a fresh sync, nothing to free yet
                out.append(l)
                continue
            out.append(f"{indent}/* BL_SYNC_FILE_FD_LEAK: close a sync-file payload before dropping it. */")
            if val == "data":
                out.append(f"{indent}if ({var}->pending_data != data)")
                out.append(f"{indent}   kbase_sync_file_waiter_free({var});")
            else:
                out.append(f"{indent}kbase_sync_file_waiter_free({var});")
            fixed.append(i + 1)
    out.append(l)

if not fixed:
    print("every payload drop already frees the sync-file waiter: nothing to do"); sys.exit(0)
p.write_text("\n".join(out))
print(f"applied: sync-file waiter freed before {len(fixed)} payload drop(s) (lines {fixed})")
