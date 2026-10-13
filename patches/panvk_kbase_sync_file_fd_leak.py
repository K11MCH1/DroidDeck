#!/usr/bin/env python3
"""PanVK on kbase leaks one file descriptor per presented frame until the process hits its fd
limit ("MESA: failed to import sync file 'Too many open files'", then "kbase: failed to
duplicate dma-buf"), after which the GPU stalls; on a Mali-G925 Steam froze after ~10 minutes.

kbase_cpu_sync_import_sync_file() dup()s the sync_file into a heap "waiter" kept in
ks->pending_data, and kbase_sync_file_waiter_free() closes it. However, every other place that
drops the payload just sets pending_data/pending_wait to NULL:
  - the CPU wait finishing successfully (the WSI path: import a dma-buf's sync_file, wait on it,
    destroy the sync — once per frame),
  - vk_sync signal and reset,
  - re-arming with panvk_kbase_sync_set_pending(),
  - moving one sync into another (the destination's payload is overwritten).
Once pending_data is NULL, finish() can no longer find the waiter, so the dup()'d fd and the
waiter struct leak. Free the sync-file waiter at each of those points (it only acts when the
payload is a sync-file waiter, so GPU-queue payloads are untouched).

No-op (exit 0) on trees without this sync code (e.g. the JM / G720 forks).
Usage: panvk_kbase_sync_file_fd_leak.py <mesa-tree>"""
import pathlib, sys

tree = pathlib.Path(sys.argv[1])
p = tree / "src/panfrost/vulkan/panvk_physical_device.c"
s = p.read_text()
if "kbase_sync_file_wait_func" not in s:
    print("no kbase sync_file waiter in this tree: nothing to do"); sys.exit(0)
if "BL_SYNC_FILE_FD_LEAK" in s:
    print("already applied"); sys.exit(0)

def sub(old, new, what, count=1):
    global s
    n = s.count(old)
    if n != count:
        sys.exit(f"{what}: expected {count} match(es), found {n}")
    s = s.replace(old, new)

TAG = "   /* BL_SYNC_FILE_FD_LEAK: close a sync-file payload before dropping it. */\n"

# signal() and reset(): both drop the payload with the mutex held.
sub("""   ks->state = KBASE_CPU_SYNC_SIGNALED;
   ks->result = VK_SUCCESS;
   ks->pending_data = NULL;
   ks->pending_wait = NULL;
   u_cnd_monotonic_broadcast(&ks->cond);""",
    """   ks->state = KBASE_CPU_SYNC_SIGNALED;
   ks->result = VK_SUCCESS;
""" + TAG + """   kbase_sync_file_waiter_free(ks);
   ks->pending_data = NULL;
   ks->pending_wait = NULL;
   u_cnd_monotonic_broadcast(&ks->cond);""", "signal")

sub("""   ks->state = KBASE_CPU_SYNC_RESET;
   ks->result = VK_SUCCESS;
   ks->pending_data = NULL;
   ks->pending_wait = NULL;
   memset(ks->targets, 0, sizeof(ks->targets));""",
    """   ks->state = KBASE_CPU_SYNC_RESET;
   ks->result = VK_SUCCESS;
""" + TAG + """   kbase_sync_file_waiter_free(ks);
   ks->pending_data = NULL;
   ks->pending_wait = NULL;
   memset(ks->targets, 0, sizeof(ks->targets));""", "reset")

# set_pending(): a new payload replaces the old one.
sub("""   assert(ks->state != KBASE_CPU_SYNC_WAITING);
   ks->pending_data = data;
   ks->pending_wait = wait;""",
    """   assert(ks->state != KBASE_CPU_SYNC_WAITING);
""" + TAG + """   if (ks->pending_data != data)
      kbase_sync_file_waiter_free(ks);
   ks->pending_data = data;
   ks->pending_wait = wait;""", "set_pending")

# CPU wait finished: nothing else touched the payload while WAITING (set_pending asserts it).
sub("""         if (result == VK_SUCCESS) {
            ks->state = KBASE_CPU_SYNC_SIGNALED;
            ks->pending_data = NULL;
            ks->pending_wait = NULL;""",
    """         if (result == VK_SUCCESS) {
            ks->state = KBASE_CPU_SYNC_SIGNALED;
""" + TAG.replace("   /*", "            /*") + """            kbase_sync_file_waiter_free(ks);
            ks->pending_data = NULL;
            ks->pending_wait = NULL;""", "wait completion")

# move(): the destination's old payload is overwritten.
sub("""   ks_dst->state = ks_src->state;
   ks_dst->result = ks_src->result;
   ks_dst->pending_data = ks_src->pending_data;""",
    """""" + TAG + """   kbase_sync_file_waiter_free(ks_dst);
   ks_dst->state = ks_src->state;
   ks_dst->result = ks_src->result;
   ks_dst->pending_data = ks_src->pending_data;""", "move")

# Every call above must come after the forward declaration of kbase_sync_file_waiter_free().
decl = s.find("kbase_sync_file_waiter_free(struct kbase_cpu_sync *ks);")
first = s.find("BL_SYNC_FILE_FD_LEAK")
if decl < 0 or decl > first:
    sys.exit("kbase_sync_file_waiter_free is not declared before its new callers")

p.write_text(s)
print("applied: sync-file waiter fds are closed whenever the payload is dropped")
