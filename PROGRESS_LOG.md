# Progress Log

Newest first. Devices only; testers are not named here.

## 2026-10-19 — Test build c5b25920 on DroidDeck 0.5.0 (CI only, not device-tested)
From the 22 logs sent since c9ebb247 (14 testers):
- **Auto could not see any open driver since 10-15:** the app read only the newest 15 releases of this repo, and the venus/gamescope component releases had pushed every PanVK pair and RADV-Xclipse past them. On every Mali, Auto then switched the Mali bridge on and cleared the Linux driver ("only Auto", "the Mali bridge is on until it is", RP4 Pro stopping at "Starting display and audio"). Fixed: this repo is read in one page of 100.
- **Auto's stand-in for a missing pair:** Mali (Venus) where the APK carries it, the bridge otherwise, nothing on a driver below Vulkan 1.2. The Linux driver is kept, nothing changes when the list could not be read, and the stand-in goes off when a pair is installed. A bridge earlier builds left on under Auto is taken as Auto's.
- **Mali bridge crash at 0x10 in vkBeginCommandBuffer** (Pixel 8 Pro G715, Lenovo TB373FU G615, Xiaomi G925): the client sent the begin info without the count the server decodes, so Mali got a zeroed begin info with stale flags. Fixed.
- **Venus:** render server no longer aborts on a destroyed mutex when a client exits holding objects (BattleTempest's patch). Component `venus-proto13-93038b7d`.
- **Mali-G1-Ultra (MT6993, arch v14):** known by its chip; Auto uses Venus. No PanVK build is proven on v14. HoloCure ran on Venus on an OPPO Find X9.
- **Galaxy S24 FE:** Secret of the Mimic, Dreamcore and Schedule I exits were Android low-memory kills (about 3 GB free), not driver faults. The app now says so on the next start.
- **In-app updater:** never installs the official (Adreno-only) build over this test build.
- **Drivers:** PanVK-Mali-G615 on GunaCharanTeja 1.1.5-FC (`c52af8b`); RADV-Xclipse-upstream on JimVulkan v1.7.0 (`0340c63`).
- **Worked on c9ebb247:** Need for Speed Most Wanted 50–60 fps (Redmi Note 14 Pro 5G, G615 pair, bridge off); Hollow Knight 33–45 fps (Lenovo TB373FU, G615 pair); Balatro ~20 min (Pixel 9a, Venus); Steam on a Pixel 8 Pro (Venus, after signing in on desktop Steam).
- **Open:** Venus OpenGL still falls back to software on G615/G610 (Zink rejects the device before creating it); Steam client segfault on Venus right after login on a Pixel 9a (no dump: /tmp/dumps not writable); 31 bridge crashes in vkbDescUpdateRaw on the Lenovo (cause unknown).

## 2026-10-16 — Two driver fixes from other Mali forks (CI only, not device-tested)
- **Steam's interface freezing on CSF Mali (G610 and newer):** one address was cut to 32 bits, so the GPU faulted and every queue stopped. Fixed in every CSF PanVK build (kbase, G615, G710, G720, and the faux123 pairs through the kbase Linux half). Found and proven on a G720 by emirvapur11; port by ryanistr.
- **Android halves that never loaded:** the JM, G615 and G710 Android drivers needed libraries Android does not have (libdrm, and for JM also zlib, zstd, libc++), so DroidDeck's screen silently used the phone's own Mali driver instead. They now ship those libraries, with libdrm renamed so the phone's own copy cannot take its place. Finding by ryanistr. On the JM pair this may change what draws the screen (see the test notes); the other Android halves needed nothing.

## 2026-10-15 — Drivers rebuilt on newer upstreams (CI only, not device-tested)
- **New manual option `radv-xclipse-upstream`:** JimVulkan's final v1.6.0, both halves (tessellation and transform feedback fixes, BC terrain fix, less BC texture memory). `radv-xclipse` stays the default on v1.6.0-RC, unchanged, because testers measured v1.6.0 about 30% slower.
- **`panvk-mali-kbase`:** zenithblue RC3 lowmem (BC1 RGB and BC7 textures in 25-33% less memory, slightly lower quality, not faster). The three faux123 pairs take this Linux half and faux123's new Android builds (RP4 Pro v0.17.0, Ace v0.40.0, RG556 v0.16.0: float blending no longer advertised where the GPU can't do it).
- **`panvk-mali-g615`:** GunaCharanTeja 1.1.4-FC (Red Dead Redemption GPU-fault fixes, fewer GPU queue stalls, faster and smaller emulated BC textures).
- Unchanged (no newer source): `panvk-mali-jm`, `panvk-mali-g720`, `panvk-mali-g710` (the G610/G710 profile uses none of the new patches).
- Sources and Android releases are now pinned per driver, so a rebuild cannot silently pick up a newer upstream.
- Redmi Note 13 Pro+ (G610) PanVK fault: a GPU "shareability" memory fault, then the GPU queues time out. Neither upstream has a fix that matches it yet.

## 2026-10-14 — Test build 42fdbfe8
- **vkbridge server:** every command buffer a device hands out is tracked. Begin, End (replay) and QueueSubmit refuse unknown or freed ones (logged, VK_ERROR_DEVICE_LOST). A per-request SIGSEGV/SIGBUS guard cuts off only the faulting client, so the app survives. The pipeline cache path is copied (it pointed at a freed JNI string). The root cause of the Mali vkBeginCommandBuffer crash is not confirmed.
- **Venus:** DROIDDECK_MALI_COMPAT_TRACE=1 in the layer. A failed glprobe adds a traced run, Mesa debug output and vulkaninfo --summary. Venus component venus-proto13-e40cd361.
- **PowerVR:** mangoapp draws with llvmpipe (it crash-looped on Zink).
- **Setup:** Xclipse gets its own support line.
- APK run 38502440987, signed via test-apk-release run 38503316327 (signer b241ea7d). Not yet run on a phone.

## 2026-10-13 — ab545368 test results (15 logs, 11 devices)
- **Pixel 10 Pro XL (PowerVR):** fixed. Steam UI boots, no drmPrimeFDToHandle errors; Brotato 60 fps, Slay the Spire 40+. Megabonk launches with no picture; Steam UI ~15 fps (software); mangoapp crash-loops 5x ("zink: could not create swapchain", GLXBadCurrentWindow).
- **Mali bridge (Edge 60 G615, Tab S11 G925):** the BInit fix works (non-exportable modifiers tried, gamescope/Xwayland/Steam start). Then SIGSEGV at addr 0x10 in the app process: libGLES_mali inside vkBeginCommandBuffer, replayed from vkb_sv_vkEndCommandBuffer, about 150 ms after the Steam client's device is created (it takes the shared-memory present fallback). Kills the whole app. Next build: fix plus fallback.
- **Venus OpenGL:** OK on G925 (glprobe passes, layer adds robustBufferAccess2/nullDescriptor). Fails on G615 and G610 in all 5 variants ("failed to load driver: zink"; the layer never loads inside glprobe), so llvmpipe. Next build: verbose zink probe.
- **PanVK:** G610 (Redmi Note 13 Pro+) CSF fatal error 0x88 → DEVICE_LOST after ~2 min. G68 (Tab S9 FE) Xwayland SIGSEGV in libgallium on its first dma-buf import. G615 (Redmi Note 14 Pro) Steam + a game, no crash.
- **Venus G68 (Tab S9 FE):** virglrenderer abort "pthread_mutex_lock called on a destroyed mutex".
- **App:** Setup labels Xclipse as "System PowerVR driver" (GpuInfo.kt supportText(context) lacks the Xclipse case). Next build.

## 2026-10-13 — Test build ab545368
- **PowerVR regression:** tools/linuxfs/preload/drm.c now uses PR #570's current same-file check. The old one failed below kernel 6.10 when Android blocks the fallback, so every PowerVR dmabuf import returned EOPNOTSUPP.
- **mangoapp:** gets an empty /sys/class/thermal when the phone hides it (it crashed 5x at start).
- **gamescope p20:**
  - patch 0132 logs which waitable hung up, its fd, and the compositor connection's error
  - patch 0133 uses driver-supported modifiers that aren't marked shareable (the bridge's BInit assert at rendervulkan.cpp:2418), or fails cleanly
- **Venus glprobe:** on a failure, reruns with loader warnings, then tries without ZINK_DEBUG=compact, with ZINK_DESCRIPTORS=auto, without kopper, and without the compat layer (that last one for the log only). Software only if all of them fail.
- Signed and published by test-apk-release.yml; announced by DroidDeck-Bot. Not yet run on a phone.

## 2026-10-13 — Results on 48d2d52d
- **Edge 60 (G615), Venus:** Steam Big Picture opens (the render-server crash fix and the YCbCr skip work). glprobe: Zink failed ("glx: failed to create drisw screen", "FAIL glXChooseVisual"), so the Steam client fell back to llvmpipe, ~4–5 fps.
- **Edge 60 (G615), bridge:** 9/9. The YCbCr retry was accepted, and the 0131 memory fallback logged "no memory type with properties 0x7 in type bits 0x3; without DEVICE_LOCAL: 1". Then an assert in rendervulkan.cpp:2418 (CVulkanTexture::BInit).
- **Pixel 10 Pro XL (PowerVR DXT-48-1536, Android 17), #570 route:** regression vs the PR #570 build. "zink: failed drmPrimeFDToHandle Operation not supported" → "XWAYLAND: importing the supplied dmabufs failed" → gamescope "X11 I/O error". Also "Permission denied: /sys/class/thermal/".
- **S24 FE, 8397965d:** R.E.P.O. and Mouse P.I. run, then gamescope "IWaitable hung up. Aborting." with no SYNCOBJ errors (explicit sync is off). Triggered after a resume, and after 60↔120 Hz flips.
- Round 6 in progress:
  - the PowerVR Xwayland fix and thermal-read tolerance
  - IWaitable logging and continuing where safe
  - bridge BInit
  - Zink on Venus (G615)

## 2026-10-13 — Test build 48d2d52d
- Results on 8397965d:
  - **Edge 60 (G615), bridge:** vkbridge passes 9/9 and is used. gamescope's YCbCr retry was accepted, then "findMemoryType failed".
  - **Edge 60 (G615), Venus:** "vkr: ring_submit_cmd: vn_dispatch_command failed" → vtest server exited 137.
  - **Narzo 60 (G57), Venus, 3ef49faa:** Steam logs in. Hotline Miami's HotlineGL.exe misses OpenAL32.dll.
  - **A15 (G57), Moonlighter:** with DROIDDECK_MALI_COMPAT_DISABLE=1, DXVK lacks fillModeNonSolid, so the run is inconclusive.
- gamescope p19 (patch 0131): the upload buffer falls back to HOST_VISIBLE without DEVICE_LOCAL on the bridge. A refused test pipeline is never destroyed.
- Venus: gamescope skips immutable YCbCr samplers up front (GAMESCOPE_NO_YCBCR_SAMPLERS=1). virglrenderer logs and ignores destroys of objects it never created (the vkDestroyPipeline of a refused pipeline killed the server). Component `venus-proto13-6199a93f`.
- OpenAL: Steam's shared package 229020 now maps to DroidDeck's OpenAL component, so games that list it get the DLLs.
- Moonlighter: investigated only. It most likely stalls on first load; a DXVK debug log was requested.
- Signed and published by test-apk-release.yml; announced by DroidDeck-Bot. Not yet run on a phone.

## 2026-10-13 — Test build 8397965d
- "Steam interface: GPU drawing" is hidden on Mali, and a saved "on" is cleared. It rebooted a Mali-G615 phone as steamwebhelper started.
- gamescope p18 (patch 0130): a composite pipeline refused at start-up is retried with a layout without immutable YCbCr samplers. On the G615 via Venus every composite shader was refused. Their SPIR-V caps were 1/43/50 (Shader, Sampled1D, ImageQuery), so fp16 was not the cause.
- Venus: `droiddeck-glprobe` opens GL through GLX like the Steam client, with `LIBGL_DEBUG=verbose`. If it fails, the client's GL goes to llvmpipe.
- vkbridge self-test: the draw check now waits for the render pass's stores before reading back. Mali's tiler wrote zeros without the dependency, so the "black draw" was the test, not the bridge.
- Moonlighter on Venus: investigated only. It most likely hangs before its first scene; next test is `DROIDDECK_MALI_COMPAT_DISABLE=1`.
- Signed and published by test-apk-release.yml. Not yet run on a phone.

## 2026-10-13 — Results on 7464bd76 / 3ef49faa
- **Galaxy A15 (Mali-G57), Venus, 7464bd76:** first games on Venus. Salt and Sanctuary and Children of Morta at ~15–30 fps. The layer emulates fillModeNonSolid, multiViewport, shaderClipDistance/CullDistance, robustBufferAccess2, textureCompressionBC and multiDrawIndirect. Moonlighter makes frames but the screen is black, with no audio.
- **Edge 60 (G615), bridge, 3ef49faa:** the image self-test passes (LAZILY_ALLOCATED fix). The draw check gives "pixel 0 = 0x00000000", so 8/9; the fallback to PanVK worked and Steam opened.
- **Edge 60 (G615), Venus, 3ef49faa:** gamescope compute pipelines fail (-3), all of them the fp16 variants (SPIR-V caps 1 43 50). Zink still "failed to load driver" even though nullDescriptor is present.
- **Edge 60 (G615), PanVK, "Steam interface: GPU drawing" on:** the phone reboots as steamwebhelper starts (the log ends NUL-padded). The S24 FE (Xclipse) is fine with it.
- **S24 FE:** processes.txt shows the "CS rejected / DEVICE_LOST" errors come from Steam's `gldriverquery` startup probe. Monster Hunter Rise still crashes before its menu.
- In progress (round 4):
  - hide GPU drawing on Mali
  - Venus gamescope without fp16
  - a Zink probe with llvmpipe fallback
  - the bridge draw path
  - Moonlighter on Venus
- Discord: the test builds and these updates are announced in the DroidDeck "Crash on mali devices" thread by DroidDeck-Bot (`announce.yml`): 7464bd76, 3ef49faa, the Mali GPU-drawing warning, and the round-4 "being fixed" notice.

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
