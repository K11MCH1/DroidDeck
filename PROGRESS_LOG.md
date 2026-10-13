# Progress Log

Newest first. Devices only; testers are not named here.

## 2026-10-12 — Mali Steam works; next build in progress
- **vivo X100 (Mali-G720):** Steam installs and logs in on PanVK-kbase, with the phone's own driver drawing the screen. That makes it the first Mali phone with Steam working. Megabonk (DirectX 11) creates its device and plays music but stays on its loading screen. Ender Magnolia (DirectX 12) crashes at start, likely because DroidDeck over-reports DirectX 12 features on Mali.
- **Dimensity 700 (Mali-G57):** a platformer was played to its first checkpoint. Issues: occasional negative-color flicker, and glitches when Steam's side menu opens.
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
