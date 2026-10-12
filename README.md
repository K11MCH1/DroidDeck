# DroidDeck drivers for Mali and Samsung Xclipse

Open-source Mesa Vulkan drivers for phones without a Snapdragon (Adreno) GPU, packaged for
[DroidDeck](https://github.com/Droid-Deck/DroidDeck). Experimental and not yet device-tested.

Downloads: the **[test release](https://github.com/The412Banner/droiddeck-nonadreno-drivers/releases/tag/nonadreno-test)**,
updated as each driver builds.

## The drivers we rebuild

| Driver | GPUs, chips and devices | Source | Author |
|---|---|---|---|
| **RADV Xclipse** | Samsung Xclipse 920 / 530 / 940. Chips: Exynos 2200, Exynos 1480, Exynos 2400 (940 is experimental). Phones: Galaxy S22 / S22+ / S22 Ultra (Exynos models), Galaxy A55, Galaxy S24 / S24+ (Exynos models). Not the Snapdragon versions of these phones, and not Exynos 1580 (Xclipse 540). | [source](https://github.com/JimVulkan/radv-xclipse) · [Android releases](https://github.com/JimVulkan/radv-xclipse/releases) | JimVulkan |
| **FristOneRR PanVK (older Mali)** | Older Mali (Job Manager): G52, G57, G68, G76, G77, G78. Chips: Helio G85 / G88 / G95 / G99 / G100, Dimensity 700 / 810 / 6020 / 6080 / 6100+ / 1080 / 1200 / 1300 / 8050, Kompanio 1300T, Unisoc T820, Exynos 1280 / 1380. Phones the author lists as working: Poco M6 Pro 4G, Galaxy A15 / A15 5G / A17 4G, Realme 10 4G, Infinix Note 30 5G / Note 50 Pro, Tecno Camon 20 Pro 5G, Redmi Note 12 Pro 5G, Redmi Note 10S, Galaxy Tab S9 FE+. | [source](https://github.com/FristOneRR-Admin/FristOneRR-Panvk-Source) · [Android releases](https://github.com/FristOneRR/FristOneRR-Panvk-Driver/releases) | FristOneRR (credits: Noysz, mexicanbr0auth, LukeValen, BossDrk) |
| **PanVK G720 (wonderkast02)** | Mali-G720 (CSF). Chips: Dimensity 9300 / 9300+, Dimensity 8400. Phones/tablets: Vivo X100 / X100 Pro, Oppo Find X7, Galaxy Tab S10+ / S10 Ultra, Poco X7 Pro, Redmi Turbo 4. | [source](https://github.com/wonderkast02/panvk-g720-kbase-csf) · [Android releases](https://github.com/wonderkast02/panvk-g720-kbase-csf/releases) | wonderkast02 |
| **PanVK kbase Android (G615)** | Mali-G615 (CSF). Chips: Dimensity 7300 (the author's test phone is an Oppo CPH2763), Dimensity 8300. Phones: Poco X6 Pro, Redmi K70E and other Dimensity 7300 / 8300 phones. | [source](https://github.com/GunaCharanTeja/panvk-kbase-android) | GunaCharanTeja (fork of zenithblue-oss/panvk-kbase-android) |

## What this repo does

Each driver comes as a pair, like DroidDeck's Adreno drivers:

- **Android half:** the author's own Android release, unchanged. It draws DroidDeck's screen.
- **Linux half:** the same driver built here from the author's public source for DroidDeck's
  desktop Linux (glibc, Arch Linux ARM). It runs Steam and the games.

`build_linux_driver.sh` cross-compiles each source against an Arch Linux ARM sysroot. Where an
Android-only fork removed desktop pieces (window-system loader, X11 helpers, some headers), they
are restored from upstream Mesa, and small stand-ins in `compat/` replace Android's logging and
property calls. `make_release.py` builds the pairs and the release notes from `drivers.json`.

## Credits

All driver work belongs to the authors above and to the [Mesa](https://gitlab.freedesktop.org/mesa/mesa)
project (MIT). Also credited by FristOneRR: Noysz, mexicanbr0auth, LukeValen and BossDrk.
