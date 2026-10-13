# Progress Log

Newest first. Devices only; testers are not named here.

## 2026-10-13 — Test build 3ef49faa
- Venus: the Mali compatibility layer runs in every process except gamescope, so Zink in Steam and Xwayland gets nullDescriptor. If it is still missing, GL falls back to llvmpipe. Null texel-buffer stand-ins added. Component `venus-proto13-55b30fbf`.
- vkbridge (#517 code): skips LAZILY_ALLOCATED memory types (Mali-G615 lists one first, so images had no memory type). If the self-test fails, the session falls back to the PanVK pair.
- Compositor: a buffer shown on two surfaces (gamescope planes while a notification is up) is released only when both let go. This is the likely cause of the notification black screen.
- gamescope p17 (patch 0129): a refused compute pipeline is logged with its SPIR-V capabilities.
- New Setup switch "Steam interface: GPU drawing". New processes.txt log on open driver pairs.
- Investigated only: Castle Crashers' missing audio (Proton Experimental placeholder audio) and PanVK D3D9 sprite glitches on G615 (likely a driver bug).
- Results on 6c7242aa (Edge 60, Narzo 60, A15, S24 FE): see the release notes. Not yet run on a phone.

## 2026-10-13 — Test build 7464bd76
- Mali compatibility layer (Venus): emulates multiDrawIndirect (split into single draws), VK_EXT_depth_clip_enable (as depth clamp) and VK_EXT_robustness2/nullDescriptor (stand-in buffer and 1x1 image). These are the DXVK 3.1 requirements these Malis lack. The layer logs which features it emulates.
- Venus component `venus-proto13-22694a38`. APK signed and published by test-apk-release.yml.
- Not yet run on a phone.

## 2026-10-13 — Test build 6c7242aa
- Venus: gamescope no longer requires VK_EXT_robustness2 (patch 0128, gamescope p16).
- PanVK fd-leak drivers: the app re-downloads a driver when its GitHub digest changes. The open-files limit is raised as a safety net.
- Mali bridge switch is saved and honored. On Mali, a PanVK pair keeps the screen on the phone's own driver (fixes the switch-back hang).
- APKs are now signed and uploaded by `.github/workflows/test-apk-release.yml`.
- First results on 1c758abd, after this build was cut:
  - Galaxy S24 FE: no explicit-sync errors any more, and Monster Hunter World runs ~30–54 fps before stopping (cause not in the log).
  - Galaxy A15 (G57) on Venus: gamescope and Steam come up on Venus. Salt and Sanctuary fails because Venus on this G57 lacks `multiDrawIndirect`, which DXVK requires.

## 2026-10-13 — PanVK kbase file-descriptor leak fixed (driver rebuilds)
- **The freeze:** the G925 Steam freeze after ~10 minutes ("failed to import sync file 'Too many open files'") is a per-frame fd leak in PanVK's kbase CPU sync.
- **The cause:** `kbase_cpu_sync_import_sync_file()` dup()s the sync_file into a waiter on `pending_data`, but the CPU-wait-complete, signal, reset, set_pending and move-destination paths dropped `pending_data` without closing it.
- **The fix:** `patches/panvk_kbase_sync_file_fd_leak.py` frees the waiter at each of those points.
  - zenithblue's tree has 5 such drops, and the G615 / G710 trees share its code.
  - wonderkast02's G720 tree has 1 (signal).
  - The JM tree doesn't have this code, so nothing changes there.
- **Rebuilt:** PanVK-Mali-kbase, G615, G710, G720, JM, and the faux123 mixed pairs (all of which use the kbase Linux half). Only the Linux halves change; the Android halves come from the authors' own builds and may have the same leak.
- **Status:** not yet tested on a device.

## 2026-10-13 — Overnight results on 1c758abd
- **Mali games run (PanVK-kbase, phone's own driver for the screen):**
  - Lenovo Legion Tab (G615): Hollow Knight at ~35–45 fps
  - Motorola Edge 60 (G615): Castle Crashers at up to ~60 fps, with graphics glitches and no game sound
  - Xiaomi 14T Pro (G720): Hades runs, with Steam sound
- **Xiaomi 15T Pro (G925):** Steam runs, then freezes after ~10 min. The log shows "Too many open files" in PanVK's sync-file import, which points to a file-descriptor leak.
- **Mali (Venus):** fails on G57, G615 and G720. gamescope reports "Missing required extension: VK_EXT_robustness2" right after it picks "Virtio-GPU Venus (Mali-…)". The Venus server and guest driver themselves work.
- **Mali bridge switch:** has no effect while a PanVK pair is in use ("in use: false").
- **Xiaomi 14T Pro:** the PanVK G720 (wonderkast02) pair stops at "Waiting for first frame".
- **Older builds:** logs from them showed the explicit-sync abort that was fixed in c359eac6.

## 2026-10-13 — Test build 1c758abd: Mali (Venus) route
- Added David Cimo's Venus route (DavidCimo/droiddeck-mali, from DroidDeck 0.3.1 + his 12 commits) as a Setup option "Mali (Venus)"; Auto stays on PanVK. Venus component (Mesa 26.2.4 Venus ICD, virglrenderer 1.3.0 render server, Mali compatibility layer) and gamescope p15 built in CI and pinned by sha.
- Not yet run on a phone in this build.

## 2026-10-13 — Test build c359eac6
- Mali: the phone's own driver always draws the screen under Auto (no driver-file lookup).
- gamescope explicit sync off on kernels older than 6.6 and on Mali (patched gamescope `gamescope-3.16.29-p14-nonadreno`, released here).
- Steam's web view composites in software with Mali / Samsung driver pairs (tile corruption).
- vkd3d-proton reports the driver's real DirectX 12 caps on PanVK / RADV (no forced 12_2 / SM 6.9).
- Sound: nothing in PulseAudio's start-up can block; fallbacks run afterwards with timeouts; a reboot hint when Android refuses the output.
- Logging: buffer attach/release tracing (G925 black screen), imported buffer formats (colour flicker), Mesa output in game logs.

## 2026-10-12 — Mali Steam works; next build in progress
- **vivo X100 (Mali-G720):** Steam installs and logs in on PanVK-kbase, with the phone's own driver drawing the screen. That makes it the first Mali phone with Steam working. Megabonk (DirectX 11) creates its device and plays music but stays on its loading screen. Ender Magnolia (DirectX 12) crashes at start, likely because DroidDeck over-reports DirectX 12 features on Mali.
- **Correction:** an earlier note listed a Dimensity 700 (Mali-G57) playing a game; that tester was on an unofficial third-party "Mali universal" DroidDeck build (Venus-based), not these drivers.
- **Xiaomi with a Dimensity 9400+ (Mali-G925):** PanVK runs on the newest Mali generation (arch v13) and Steam starts, but the screen stays black. gamescope logs "Compositor released us but we were not acquired", which points to a buffer hand-off bug in DroidDeck's screen code.
- **Galaxy Tab S9 FE (Mali-G68) and Redmi Note 13 Pro+ (Mali-G610):** both stop at "Waiting for Steam's first frame". DroidDeck didn't find the phone's own Vulkan driver file, so it fell back to PanVK's Android half for the screen, which Mali's gralloc rejects.
- **Galaxy S24 FE (Xclipse 940), RADV:**
  - Games run (R.E.P.O. ~23–30 fps), frame generation x2 works, and the KDE desktop and Firefox work.
  - Sound works, but one phone needed a reboot first: Android's audio service was stuck ("DISCONNECTED").
  - Steam's UI shows tile corruption while scrolling, and the library drops to 1–18 fps.
  - Trackmania hangs: gamescope's explicit sync needs `DRM_IOCTL_SYNCOBJ_EVENTFD`, which Linux 6.1 doesn't have.
- **Not a driver problem:** none of these needed a driver rebuild. Every driver is current with its upstream source.

## 2026-10-12 — The drivers work inside DroidDeck
- **PanVK Linux halves:** they load and find the GPU on Mali-G57, G68, G610, G720 and G925.
- **DRM node patch:** every PanVK build now reports the kbase device as its DRM primary/render node (`patches/panvk_kbase_drm_node.py`). That fixes gamescope's "physical device has no primary node".
- **RADV Xclipse:** first non-Snapdragon phone to boot Steam (Galaxy S24 FE).

## 2026-10-12 — Releases
- Nine driver releases, each an Android + Linux pair in DroidDeck's driver-bundle layout:
  - RADV Xclipse
  - PanVK-kbase (zenithblue, Mali v9–v13)
  - FristOneRR PanVK (older Mali)
  - PanVK G720, G615 and G710
  - faux123's three handheld builds (paired with our PanVK-kbase Linux half)
- One workflow and one release per driver, replaced in place on every rebuild.
- A DroidDeck test build release (`droiddeck-test-non-adreno-all`) picks the right pair automatically for each phone.

## 2026-10-12 — Start
- glibc builds of Android-only Mesa forks for DroidDeck's Linux runtime:
  - restore the desktop pieces the forks removed (loader, X11, headers) from upstream Mesa
  - stand-ins for Android logging and properties (`compat/`)
  - PanVK build tools (`mesa_clc`, `panfrost_compile`) built natively first
