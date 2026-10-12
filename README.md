# DroidDeck non-Adreno drivers

glibc (desktop Linux) builds of two open-source Mesa Vulkan drivers, for DroidDeck's Linux runtime:

| Zip | GPUs | Source |
|---|---|---|
| `RADV-Xclipse-Linux.zip` | Samsung Xclipse 920 / 530 / 940 | [JimVulkan/radv-xclipse](https://github.com/JimVulkan/radv-xclipse) (MIT) |
| `PanVK-Mali-kbase-Linux.zip` | Mali on Arm's kbase kernel driver (G52, G57, G68, G76, G77, G78…) | [FristOneRR-Admin/FristOneRR-Panvk-Source](https://github.com/FristOneRR-Admin/FristOneRR-Panvk-Source) ([driver releases](https://github.com/FristOneRR/FristOneRR-Panvk-Driver)) |

The upstream releases are Android builds for Winlator-style apps. These are the same sources built against glibc (Arch Linux ARM sysroot) so they load inside DroidDeck's Linux. All credit for the drivers goes to their authors.

Experimental: not yet tested on a device.
