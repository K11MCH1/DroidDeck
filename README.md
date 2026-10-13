# DroidDeck drivers for Mali and Samsung Xclipse

Open-source Mesa Vulkan drivers for phones without a Snapdragon (Adreno) GPU, packaged for
[DroidDeck](https://github.com/Droid-Deck/DroidDeck). Experimental and not yet device-tested. Nine driver releases plus a DroidDeck test build.

Progress and test results: [PROGRESS_LOG.md](PROGRESS_LOG.md).

Downloads: the **[Releases page](https://github.com/The412Banner/droiddeck-nonadreno-drivers/releases)** (one release per driver,
updated in place on every rebuild).

## DroidDeck test build

To use these drivers, testers need the DroidDeck test build, which picks the right driver automatically:
**[DroidDeck test build: non-Snapdragon](https://github.com/The412Banner/droiddeck-nonadreno-drivers/releases/tag/droiddeck-test-non-adreno-all)**
(branch [`test/non-adreno-all`](https://github.com/Droid-Deck/DroidDeck/tree/test/non-adreno-all); not an official DroidDeck release).

| Phone | Driver DroidDeck picks automatically | Other choices in the driver settings |
|---|---|---|
| Snapdragon (Adreno) | Turnip, unchanged | the usual Turnip versions |
| Pixel 10 / 11 (PowerVR) | the phone's own driver | none |
| Samsung Exynos (Xclipse) | RADV Xclipse (booted Steam and ran a game on a Galaxy S24 FE) | the phone's own driver, Mali bridge |
| Mali v9 to v13 on Android 15+ (G57 / G68 / G77 / G78, G610 / G710, G615 / G715, G720 / G725, G925) | PanVK-kbase (zenithblue) | the per-chip PanVK pair, the faux123 pair on its handheld, Mali bridge |
| Mali on Android 14 or older | the per-chip PanVK pair | Mali bridge |
| Mali-G52 / G76 | FristOneRR PanVK | Mali bridge |
| Any other Mali | Mali bridge (turned on automatically) | none |

**Results so far:** Samsung Galaxy S24 FE (Xclipse 940) with RADV Xclipse boots Steam and runs games (R.E.P.O. ~23-30 fps; a no-sound fix is in the newest build). Mali: the Linux driver loads and finds the GPU (Mali-G610); reaching Steam is being tested with the newest build.

Report results with DroidDeck's session logs (Setup > Share logs) in the DroidDeck Discord testing thread, and say which driver was in use.

## The drivers we rebuild

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

## Devices checked so far

Testers ran a quick capability check (Vulkan Caps Viewer + one Termux command) on their phones. Nothing has been run in DroidDeck yet.

| Device | GPU | Phone's own driver | GPU device open from an app | Driver to try |
|---|---|---|---|---|
| Xiaomi 14T Pro | Mali-G720 Immortalis MC12 (Dimensity 9300+) | Vulkan 1.3.247 | `/dev/mali0` yes | PanVK-kbase (zenithblue) or PanVK-Mali-G720 |
| Google Pixel 7 Pro | Mali-G710 (Tensor G2) | Vulkan 1.4.343, all needed extensions | `/dev/mali0` yes | PanVK-kbase (zenithblue) or PanVK-Mali-G710 |
| Samsung Galaxy S24 FE | Xclipse 940 (Exynos 2400e) | Vulkan 1.3.279, all needed extensions | `/dev/dri/renderD128` yes | RADV-Xclipse |
| Samsung Galaxy Tab S11 | Mali-G925 Immortalis MC12 (Dimensity 9400+) | Vulkan 1.3.278, all needed extensions | `/dev/mali0` yes | PanVK-kbase (zenithblue) |

## What this repo does

Each driver comes as a pair, like DroidDeck's Adreno drivers:

- **Android half:** the author's own Android release, unchanged. It draws DroidDeck's screen.
- **Linux half:** the same driver built here from the author's public source for DroidDeck's
  desktop Linux (glibc, Arch Linux ARM). It runs Steam and the games.

`build_linux_driver.sh` cross-compiles each source against an Arch Linux ARM sysroot. Where an
Android-only fork removed desktop pieces (window-system loader, X11 helpers, some headers), they
are restored from upstream Mesa, and small stand-ins in `compat/` replace Android's logging and
property calls. Each driver has its own workflow (`.github/workflows/<driver>.yml`, all using `_driver.yml`) and its own release, which is replaced in place on every rebuild. `make_release.py` builds the pair and the release notes from `drivers.json`. To rebuild one driver from a different source commit, run its workflow with `src_ref`.

## Credits

All driver work belongs to the authors above and to the [Mesa](https://gitlab.freedesktop.org/mesa/mesa)
project (MIT). Also credited by FristOneRR: Noysz, mexicanbr0auth, LukeValen and BossDrk.
