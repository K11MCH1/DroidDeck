#!/usr/bin/env python3
"""PanVK on kbase has no DRM node, so VK_EXT_physical_device_drm reports neither a primary nor a
render node and gamescope stops with "physical device has no primary node". Report the kbase
device (/dev/mali0) itself as both, the way DroidDeck's Turnip reports /dev/kgsl-3d0
(Banners-Turnip patches/linux/kgsl-drm-node.patch). DroidDeck exposes the device at a DRM path
in the guest; BL_DRM_STANDIN, when set, names that path and is reported instead.
Usage: panvk_kbase_drm_node.py <mesa-tree>"""
import pathlib, sys

tree = pathlib.Path(sys.argv[1])
p = tree / "src/panfrost/vulkan/panvk_physical_device.c"
s = p.read_text()
if "BL_DRM_STANDIN" in s:
    print("already applied"); sys.exit(0)
anchor = "   result = create_kmod_dev_kbase(device, instance, path);\n   if (result != VK_SUCCESS)\n      return result;\n"
if anchor not in s:
    sys.exit("panvk_physical_device_init_kbase: create_kmod_dev_kbase anchor not found")
add = anchor + """
   /* kbase has no DRM nodes: report the kbase device (or DroidDeck's stand-in DRM path for it)
    * as both primary and render node, so VK_EXT_physical_device_drm names a device a Wayland
    * compositor (gamescope) can match. */
   {
      const char *standin = getenv("BL_DRM_STANDIN");
      struct stat kbase_st;
      if (stat(standin && *standin ? standin : path, &kbase_st) == 0 &&
          S_ISCHR(kbase_st.st_mode)) {
         device->drm.primary_rdev = kbase_st.st_rdev;
         device->drm.render_rdev = kbase_st.st_rdev;
      }
   }
"""
s = s.replace(anchor, add, 1)
for inc in ("#include <sys/stat.h>", "#include <stdlib.h>"):
    if inc not in s:
        s = s.replace("#include ", inc + "\n#include ", 1)
p.write_text(s)
print("applied: kbase device reported as DRM primary/render node")
