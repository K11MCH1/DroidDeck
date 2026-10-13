# Progress Log

Newest first. Devices only; testers are not named here.

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
