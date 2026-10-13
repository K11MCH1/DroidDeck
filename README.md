# DroidDeck on Mali and Samsung Xclipse

Graphics drivers and a DroidDeck test build for phones **without** a Snapdragon (Adreno) GPU.
Experimental community testing. Not an official DroidDeck release.

- **Test build (APK):** [DroidDeck test build: non-Snapdragon](https://github.com/The412Banner/droiddeck-nonadreno-drivers/releases/tag/droiddeck-test-non-adreno-all), built from the branch [`test/non-adreno-all`](https://github.com/Droid-Deck/DroidDeck/tree/test/non-adreno-all) of [DroidDeck](https://github.com/Droid-Deck/DroidDeck)
- **Drivers:** the [Releases page](https://github.com/The412Banner/droiddeck-nonadreno-drivers/releases) has one release per driver, replaced in place on every rebuild
- **Progress and test results:** [PROGRESS_LOG.md](PROGRESS_LOG.md) and the test build's release notes
- **Newest test build: `3ef49faa`.** Steam's OpenGL on Mali (Venus), the Mali bridge memory fix with a safe fallback to PanVK, the notification black-screen fix, and a Steam "GPU drawing" setting. `7464bd76` added the GPU features DXVK needs on Venus. Since `6c7242aa`, the builds also have the Venus screen fix, the fixed PanVK drivers (no more freeze after ~10 minutes), a working Mali bridge switch, and the switch-back fix.
- **⚠️ Mali phones: don't turn on "Steam interface: GPU drawing".** On Mali it can reboot the phone. It's meant for Samsung (Xclipse), and the next build hides it on Mali.
- **Where things stand (devices only):**
  - **First games on Mali (Venus):** Salt and Sanctuary and Children of Morta run at ~15–30 fps on a Galaxy A15 (Mali-G57), with no glitches.
  - **Mali games on PanVK:**
    - Hollow Knight on a Lenovo Legion Tab (G615)
    - Celeste and Castle Crashers on a Motorola Edge 60 (G615), with picture glitches
    - Hades on a Xiaomi 14T Pro (G720)
  - **Mali bridge:** creates images on the Edge 60 now. Drawing is still black, so it falls back to PanVK and Steam opens.
  - **Samsung S24 FE (Xclipse):** games run on RADV. Monster Hunter Rise boots but crashes before its menu.
  - **Being fixed next:**
    - Venus on the Mali-G615 (helper shaders and Steam's OpenGL)
    - the bridge's black drawing
    - Moonlighter's black screen on Venus
    - hiding "GPU drawing" on Mali
  - Full list in the test build's release notes.
- **Get the test build only from the link above.** Other copies (for example on file-sharing sites) are not ours.

## How graphics work on each kind of phone

DroidDeck runs Steam and games inside a desktop Linux on the phone. Its normal driver, Turnip, only
works on Snapdragon. The test build adds these routes for other GPUs:

| Route | What it does | Where it comes from |
|---|---|---|
| **Open driver pairs** (PanVK for Mali, RADV for Xclipse) | An open-source Mesa driver runs Steam and games; the phone's own driver (or the pair's Android half) draws DroidDeck's screen | The drivers below, rebuilt here |
| **Mali (Venus)** | Mesa's Venus driver sends every Vulkan command to a small server in the app, which runs it on the **phone's own Mali driver**; a compatibility layer adds the features DXVK needs | [David Cimo's DroidDeck Mali port](https://github.com/DavidCimo/droiddeck-mali) (in the test build, turned on in Setup) |
| **Phone's own driver** (PowerVR, Xclipse fallback) | Steam and games use the phone's own Vulkan driver through libhybris | [DroidDeck PR #570](https://github.com/Droid-Deck/DroidDeck/pull/570) |
| **Mali bridge** | A Vulkan bridge to the phone's own Mali driver | [DroidDeck PR #517](https://github.com/Droid-Deck/DroidDeck/pull/517) |

What the test build picks automatically (every choice can be changed in the driver settings):

| Phone | Automatic choice | Other choices |
|---|---|---|
| Snapdragon (Adreno) | Turnip, unchanged | the usual Turnip versions |
| Pixel 10 / 11 (PowerVR) | the phone's own driver | none |
| Samsung Exynos (Xclipse) | RADV Xclipse | the phone's own driver, Mali bridge |
| Mali v9 to v13 on Android 15+ (G57 / G68 / G77 / G78, G610 / G710, G615 / G715, G720 / G725, G925) | PanVK-kbase (zenithblue), with the phone's own driver drawing the screen | the per-chip PanVK pair, the faux123 pair on its handheld, Mali (Venus), Mali bridge |
| Mali on Android 14 or older | the per-chip PanVK pair | Mali (Venus), Mali bridge |
| Mali-G52 / G76 | FristOneRR PanVK | Mali (Venus), Mali bridge |
| Any other Mali | Mali bridge | Mali (Venus) |

Report results with **Setup > Share logs** in the DroidDeck Discord testing thread, and say which route was in use.

## The open drivers we rebuild

| Driver | GPUs, chips and devices | Source | Our release / build | Author |
|---|---|---|---|---|
| **RADV Xclipse** | Samsung Xclipse 920 / 530 / 940. Chips: Exynos 2200, Exynos 1480, Exynos 2400 / 2400e (940 is experimental). Phones: Galaxy S22 / S22+ / S22 Ultra (Exynos models), Galaxy A55, Galaxy S24 / S24+ (Exynos models), Galaxy S24 FE. Not the Snapdragon versions of these phones, and not Exynos 1580 (Xclipse 540). | [source](https://github.com/JimVulkan/radv-xclipse) · [Android releases](https://github.com/JimVulkan/radv-xclipse/releases) | [release](https://github.com/The412Banner/droiddeck-nonadreno-drivers/releases/tag/radv-xclipse) · [build](https://github.com/The412Banner/droiddeck-nonadreno-drivers/actions/workflows/radv-xclipse.yml) | JimVulkan |
| **PanVK-kbase (zenithblue, all newer Mali: v9 to v13)** | One driver for Mali v9 to v13 on Arm's kbase driver: G57 / G68 / G77 / G78 (v9), G610 / G710 (v10), G615 / G715 (v11), G720 (v12), G925 / G725 (v13). Author-tested (PanProbe 38/38): Lenovo Tab TB336FU (G57), Poco X6 Pro (G615), Galaxy Tab S10 Ultra (G720), Motorola Edge 40 Neo (G610), Pixel 7 / 7a (G710), Pixel 8 / 9 (G715); Galaxy Tab S11 Ultra (G925) passed on the previous beta. Chips include Helio G99, Dimensity 7300 / 8300 / 9000 / 9300 / 9400, Tensor G2 / G3 / G4. Android 15 or newer (the author's Android build needs API 35). | [source](https://github.com/zenithblue-oss/panvk-kbase-android) · [Android releases](https://github.com/zenithblue-oss/panvk-kbase-android/releases) | [release](https://github.com/The412Banner/droiddeck-nonadreno-drivers/releases/tag/panvk-mali-kbase) · [build](https://github.com/The412Banner/droiddeck-nonadreno-drivers/actions/workflows/panvk-mali-kbase.yml) | zenithblue-oss |
| **FristOneRR PanVK (older Mali)** | Older Mali (Job Manager): G52, G57, G68, G76, G77, G78. Chips: Helio G85 / G88 / G95 / G99 / G100, Dimensity 700 / 810 / 6020 / 6080 / 6100+ / 1080 / 1200 / 1300 / 8050, Kompanio 1300T, Unisoc T820, Exynos 1280 / 1380. Phones the author lists as working: Poco M6 Pro 4G, Galaxy A15 / A15 5G / A17 4G, Realme 10 4G, Infinix Note 30 5G / Note 50 Pro, Tecno Camon 20 Pro 5G, Redmi Note 12 Pro 5G, Redmi Note 10S, Galaxy Tab S9 FE+. | [source](https://github.com/FristOneRR-Admin/FristOneRR-Panvk-Source) · [Android releases](https://github.com/FristOneRR/FristOneRR-Panvk-Driver/releases) | [release](https://github.com/The412Banner/droiddeck-nonadreno-drivers/releases/tag/panvk-mali-jm) · [build](https://github.com/The412Banner/droiddeck-nonadreno-drivers/actions/workflows/panvk-mali-jm.yml) | FristOneRR (credits: Noysz, mexicanbr0auth, LukeValen, BossDrk) |
| **PanVK G720 (wonderkast02)** | Mali-G720 (CSF). Chips: Dimensity 9300 / 9300+, Dimensity 8400. Phones/tablets: Vivo X100 / X100 Pro, Oppo Find X7, Galaxy Tab S10+ / S10 Ultra, Poco X7 Pro, Redmi Turbo 4. | [source](https://github.com/wonderkast02/panvk-g720-kbase-csf) · [Android releases](https://github.com/wonderkast02/panvk-g720-kbase-csf/releases) | [release](https://github.com/The412Banner/droiddeck-nonadreno-drivers/releases/tag/panvk-mali-g720) · [build](https://github.com/The412Banner/droiddeck-nonadreno-drivers/actions/workflows/panvk-mali-g720.yml) | wonderkast02 |
| **PanVK kbase Android (G615)** | Mali-G615 (CSF). Chips: Dimensity 7300 (the author's test phone is an Oppo CPH2763), Dimensity 8300. Phones: Poco X6 Pro, Redmi K70E and other Dimensity 7300 / 8300 phones. | [source](https://github.com/GunaCharanTeja/panvk-kbase-android) | [release](https://github.com/The412Banner/droiddeck-nonadreno-drivers/releases/tag/panvk-mali-g615) · [build](https://github.com/The412Banner/droiddeck-nonadreno-drivers/actions/workflows/panvk-mali-g615.yml) | GunaCharanTeja (fork of zenithblue-oss/panvk-kbase-android) |
| **PanVK kbase Android (G610 / G710, experimental)** | Mali-G610 / G710 (CSF, arch v10). Chips: Google Tensor G2 and Dimensity 9000 / 9000+ (Mali-G710), Dimensity 7200 / 8000 / 8100 / 8200 (Mali-G610). Devices: Pixel 7 / 7 Pro / 7a, Pixel Fold, Pixel Tablet, OnePlus Nord 3, Nothing Phone (2a), Redmi Note 13 Pro+. | [source](https://github.com/GunaCharanTeja/panvk-kbase-android) | [release](https://github.com/The412Banner/droiddeck-nonadreno-drivers/releases/tag/panvk-mali-g710) · [build](https://github.com/The412Banner/droiddeck-nonadreno-drivers/actions/workflows/panvk-mali-g710.yml) | GunaCharanTeja (fork of zenithblue-oss/panvk-kbase-android) |
| **PanVK faux123 (Retroid Pocket 4 Pro)** | Retroid Pocket 4 Pro only (Dimensity 1100, Mali-G77 MC9). Tuned and tested by the author on that handheld. | [source](https://github.com/faux123/panvk-faux123-driver-rp4pro) · [Android releases](https://github.com/faux123/panvk-faux123-driver-rp4pro/releases) | [release](https://github.com/The412Banner/droiddeck-nonadreno-drivers/releases/tag/panvk-faux123-rp4pro) · [build](https://github.com/The412Banner/droiddeck-nonadreno-drivers/actions/workflows/faux123-mixed.yml) | faux123 (proof of concept, no support from the author) |
| **PanVK faux123 (GameForce Ace)** | GameForce Ace only (Mali-G610). Tuned and tested by the author on that handheld. | [source](https://github.com/faux123/panvk-faux123-driver-ace) · [Android releases](https://github.com/faux123/panvk-faux123-driver-ace/releases) | [release](https://github.com/The412Banner/droiddeck-nonadreno-drivers/releases/tag/panvk-faux123-ace) · [build](https://github.com/The412Banner/droiddeck-nonadreno-drivers/actions/workflows/faux123-mixed.yml) | faux123 (proof of concept, no support from the author) |
| **PanVK faux123 (Anbernic RG556)** | Anbernic RG556 only (Unisoc T820, Mali-G57). Tuned and tested by the author on that handheld. | [source](https://github.com/faux123/panvk-faux123-driver-rg556) · [Android releases](https://github.com/faux123/panvk-faux123-driver-rg556/releases) | [release](https://github.com/The412Banner/droiddeck-nonadreno-drivers/releases/tag/panvk-faux123-rg556) · [build](https://github.com/The412Banner/droiddeck-nonadreno-drivers/actions/workflows/faux123-mixed.yml) | faux123 (proof of concept, no support from the author) |

## Components

Parts the test build downloads by checksum (not for users to install by hand):

- **[Mali (Venus) component](https://github.com/The412Banner/droiddeck-nonadreno-drivers/releases/tag/venus-proto13-97963459):**
  - Mesa's Venus Vulkan driver for DroidDeck's Linux
  - virglrenderer's render server for Android
  - the Mali compatibility layer

  Built from David Cimo's sources by the test branch's CI.
- **Patched gamescope** ([p17](https://github.com/The412Banner/droiddeck-nonadreno-drivers/releases/tag/gamescope-3.16.29-p17-nonadreno)): DroidDeck's gamescope with these additions:
  - a switch to turn off explicit sync on kernels that can't support it (Linux older than 6.6, and Mali)
  - David Cimo's patch for showing frames that arrive as plain shared-memory images (Venus)
  - running without `VK_EXT_robustness2`, which Venus doesn't offer on most Malis
  - logging which compute shader a GPU refuses, with the features it needs
- **Test APK signing:** `.github/workflows/test-apk-release.yml` signs a test-branch build into its four variants and replaces the release's APKs, all on GitHub.

## What this repo does

Each open driver comes as a pair, like DroidDeck's Adreno drivers:

- **Android half:** usually the author's own Android release, unchanged. G615 / G710 have no official Android build, so theirs is built here.
- **Linux half:** the same driver built here from the author's public source for DroidDeck's desktop Linux (glibc, Arch Linux ARM). It runs Steam and the games.

How the builds work:

- **Cross-compiling:** `build_linux_driver.sh` cross-compiles each source against an Arch Linux ARM sysroot.
- **Android-only forks:** where a fork removed desktop pieces (window-system loader, X11 helpers, some headers), they are restored from upstream Mesa, and small stand-ins in `compat/` replace Android's logging and property calls.
- **PanVK patches:** every PanVK build carries two patches:
  - `patches/panvk_kbase_drm_node.py`, so the Mali device shows up as a GPU to DroidDeck's screen manager
  - `patches/panvk_kbase_sync_file_fd_leak.py`, which fixes a per-frame file leak that froze the GPU after about 10 minutes
- **Workflows and releases:**
  - each driver has its own workflow (`.github/workflows/<driver>.yml`, all using `_driver.yml`) and its own release
  - `make_release.py` builds the pair and its notes from `drivers.json`
  - to rebuild one driver from a different source commit, run its workflow with `src_ref`

## Using these outside DroidDeck

The Android halves (`-Android.zip`) are standard AdrenoTools-style driver packages. They also work in Winlator-style apps such as Bannerlator, and on Mali usually go through a Vulkan wrapper. The Linux halves are only for desktop-Linux (glibc) runtimes.

## Credits

All driver and graphics work belongs to its authors. This repo only rebuilds their source for DroidDeck's Linux, repackages their Android releases as pairs, and builds the components.

**Drivers**
- **RADV Xclipse:** [JimVulkan](https://github.com/JimVulkan/radv-xclipse)
- **PanVK-kbase:** [zenithblue-oss](https://github.com/zenithblue-oss/panvk-kbase-android)
- **PanVK G615 / G710:** [GunaCharanTeja](https://github.com/GunaCharanTeja/panvk-kbase-android), a fork of zenithblue-oss's project
- **FristOneRR PanVK:** [FristOneRR](https://github.com/FristOneRR/FristOneRR-Panvk-Driver) ([source](https://github.com/FristOneRR-Admin/FristOneRR-Panvk-Source)), with work FristOneRR credits to Noysz, mexicanbr0auth, LukeValen and BossDrk
- **PanVK G720:** [wonderkast02](https://github.com/wonderkast02/panvk-g720-kbase-csf)
- **Device builds:** [faux123](https://github.com/faux123) for the Retroid Pocket 4 Pro, GameForce Ace and Anbernic RG556

**Routes in the DroidDeck test build**
- **Mali (Venus):** [David Cimo](https://github.com/DavidCimo), [DavidCimo/droiddeck-mali](https://github.com/DavidCimo/droiddeck-mali)
  - the Venus port, the Mali compatibility layer, the Venus queue-submit fix, cached frame readback, and the gamescope shared-memory patch
- **PowerVR and Xclipse through the phone's own driver:** [wallentx](https://github.com/wallentx), [PR #570](https://github.com/Droid-Deck/DroidDeck/pull/570); Xclipse support in it by [stefanz92](https://github.com/stefanz92)
- **Mali bridge:** [ASEbrahim](https://github.com/ASEbrahim), [PR #517](https://github.com/Droid-Deck/DroidDeck/pull/517)
- **Compositor safety fixes and Pixel compatibility tools:** [Leask](https://github.com/Leask), [PR #560](https://github.com/Droid-Deck/DroidDeck/pull/560), [#561](https://github.com/Droid-Deck/DroidDeck/pull/561), [#602](https://github.com/Droid-Deck/DroidDeck/pull/602)

**Foundations**
- [Mesa](https://gitlab.freedesktop.org/mesa/mesa) (MIT), including PanVK, RADV and Venus
- [virglrenderer](https://gitlab.freedesktop.org/virgl/virglrenderer)
- [gamescope](https://github.com/ValveSoftware/gamescope)
- [DroidDeck](https://github.com/Droid-Deck/DroidDeck) (GPL-3.0)
