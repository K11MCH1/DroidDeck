# Steam UI on Adreno 740 (driver 0.676.1): GPU compositing investigation

Status as of 2026-10-24: root cause found and fixed (see Resolution). Device: vivo X90 Pro-class phone, serial `10ACCC38UD000YT`, Snapdragon 8 Gen 2,
Adreno 740, Qualcomm proprietary Vulkan driver 512.676.1 (Vulkan 1.3.128). Reference device that works:
RedMagic, Adreno 840, driver v891.7 (serial `9125335101BA`).

Scripts, the replayable capture and images are in `build/research/steam-ui-740/` (git-ignored).

## Resolution

Root cause: on Adreno driver 512.676.1, pipelines created with `VK_DYNAMIC_STATE_COLOR_WRITE_ENABLE_EXT` blend against a
destination of zero (writes still land; blended draws never see what is under them). Zink adds that dynamic state to
every pipeline when `VK_EXT_color_write_enable` is present. Found by replaying an edited capture on the 740: removing the
dynamic state gave the exact expected mask values (28,41,64,169), (18,37,62,246), (3,4,6,27). Ruled out on the way:
blend factors, shader, topology, render-pass split, `LOAD` vs `CLEAR`, attachment layout, `MUTABLE_FORMAT` /
`INPUT_ATTACHMENT`, `STORAGE` usage, `LINEAR` tiling and the compat layer.

Fix: `tools/qualcomm/zink-qualcomm-color-write-enable.patch` (in `build_zink.py`) turns off Zink's use of the extension
for `VK_DRIVER_ID_QUALCOMM_PROPRIETARY`. Built in the RedMagic build root, pinned in `runtime.json`; the Zink < GL 4.0
software gate in `droiddeck-session` is removed. Verified live: 8 Gen 2 correct at 59.8 rAF fps (was 6.8 in software),
840 correct at 60.

Still open on the 740 (branch `prop-a750` holds this work; not pushed):

- Small blue streaked blocks above the cover row when the first capsule is focused (also present in the earlier broken
  GPU screenshots, absent on the 840). Not investigated yet; capture that state with `scripts/rdoc-run.sh` and follow
  it with `rdoc-graph.py` / `rdoc-batch.sh`.
- The user sees the far-right thumbnail glitch while scrolling. Not reproduced yet and not yet described in detail
  (flicker, garbled, late pop-in or smear). What was checked:
  - RenderDoc multi-frame captures stall Chromium's animation, so use them only for static states.
  - `scripts/cdp-screencast.py` records Chromium's own composited frames (DevTools `Page.startScreencast`, ~50 fps)
    without stalling it.
  - `scripts/dual-capture.sh` records that screencast and real-screen `screencap`s together, with device timestamps.
    `scripts/dual-compare.py` matches them at the far-right cover.
  - In run `dual/base` the screen matched Chromium at rest, and Chromium's own frames showed no dropouts at the right
    edge.
  - `--ui-disable-partial-swap` (`BL_STEAM_WEBHELPER_ARGS`) made the right edge look steadier in one burst. That was
    not confirmed; carousel bounce-backs from the input method confused the earlier bursts.
  - Next: get the user's description, then compare screen against screencast during motion with frame-accurate
    timing (screencap is ~2 per second; consider `screenrecord` plus a decoder).

Building Zink on the RedMagic: `files/proot-root.sh` with `BUILD_ROOT_DIR=.../files/buildroot`; pacman needs network,
which Android blocks for the app while it is in the background, so bring DroidDeck to the foreground first
(`am start -n com.droiddeck.launcher.xr/com.droiddeck.launcher.LauncherDark`). Mesa's Python modules
(python-mako/markupsafe/packaging/yaml) are now installed there. Built output: `build/qualcomm-zink/runtime`
(previous build kept in `build/qualcomm-zink/runtime-prev`).

## Problem

With GPU compositing (Chromium → ANGLE GL backend → Zink → WSI layer → compat layer → Qualcomm driver), the
Steam Big Picture UI on the 740 is fast (~59 fps rAF) but broken: black page background, missing avatar and
tab row, the STEAM pill text drawn as solid bars, black blocks in the selected cover, hero art missing.
The capability gate in `droiddeck-session` (`bl_qualcomm_browser_gpu`, Zink < GL 4.0 → `-cef-disable-gpu`)
makes it correct but slow: ~6.8 fps rAF while moving between thumbnails. The user wants a path that is both
correct and fast.

## Measurements (rAF fps while moving, 8 Gen 2)

| Config | Path | rAF fps | UI |
|---|---|---|---|
| software (current gate) | ANGLE_SWIFTSHADER, gpu_compositing disabled | 6.8 | correct |
| `BL_STEAM_CEF_SOFTWARE=0` | ANGLE_OPENGL on Zink GL 3.2 | 59.3 | broken |
| `--use-angle=vulkan` | ANGLE_VULKAN but gpu_compositing disabled_software | 5.1 | correct, slow |
| `--use-angle=vulkan --enable-features=Vulkan,VulkanFromANGLE,DefaultANGLEVulkan` | same, still software compositing | 5.3 | slow |
| `--disable-gpu-rasterization` | GPU compositing, CPU raster | 55.7 | text OK, background/blocks still broken |

## Ruled out (identical damage, pixel for pixel)

Compat-layer shader rewrites off; `ZINK_DEBUG=norp`, no `compact`, `noreorder`, `sync`, `flushsync`,
`nogeneral`; `MESA_NO_ERROR=0`; `mesa_glthread=false`; old runtime/old Mesa/old WSI;
`--ui-disable-partial-swap`; `glx_disable_ext_buffer_age=true`; `--use_virtualized_gl_contexts`.
Steam starts the browser with `--in-process-gpu`, so `--gpu-launcher` does not work.

## RenderDoc findings

1. **Rendering, not presentation.** RenderDoc's read-back of the image Zink presents
   (`capture/webhelper_frame4480.png`) shows the same damage as the screen. The WSI/SHM present path is not
   the cause.
2. **Validation layer (core + synchronization) on the browser:** only 3 benign VUIDs (A8_UNORM format query,
   conditional-rendering buffer usage bits, swapchain semaphore reuse). No sync hazards, no layout errors
   (`capture/vvl.log`). Zink's Vulkan stream is valid.
3. **Replay on the 740 reproduces it.** In pass `vkCmdBeginRendering@1374` (target image 6524, RGBA8
   1664x576, loadOp CLEAR, layout GENERAL):
   - draw 1 (pipeline 5308, indexed triangle list, src-over) copies the hero art 83077 in correctly;
   - draws 2–4 (pipeline 6541, non-indexed 4-vertex strip, blend `ZERO / SRC_ALPHA` = Chromium DstIn mask,
     sampling mask tiles 6919 / 4564 / 4553) write **(0,0,0,0)** over their whole regions.
   - Pixel history at 6524 (900,300): before (0.208,0.302,0.427,1.0), shader output (0,0,0,0.753),
     written (0,0,0,0); expected (0.157,0.227,0.322,0.753) (`capture/pixel.txt`).
   - 6528 and the swapchain then lack the hero art (`images/sheet-hero.png`).
4. **Replay experiments on the 740** (capture XML edited, rebuilt, replayed; mask region values):

   | Variant | Change | Result |
   |---|---|---|
   | v1 | alpha eq → (DST_ALPHA, ZERO) | 0 everywhere, alpha 0 too |
   | v4 | src color factor ONE | 0 |
   | v5 | blending disabled | shader alpha written correctly (27 / 169 / 246) |
   | v9 | src-over (ONE, 1−SRC_ALPHA) | (0,0,0,169) = source only, destination read as 0 |
   | v10 | dst-out (ZERO, 1−SRC_ALPHA) | 0 |
   | p1 | fragment shader made non-trivial (push-constant select) | 0 |
   | t1 | topology strip → triangle list | drawn triangles still 0 (`images/sheet-t1.png`) |
   | l1 | pass loadOp CLEAR → LOAD | 0 |

   **Conclusion so far:** for these draws the blender reads the destination as 0 (v9 is the clearest).
   It is not the blend factors, the shader, the topology or the fast-clear path. Not yet varied: whether
   *any* draw after the first in a dynamic-rendering pass can read the previous draw's output on this driver
   (draw 1 in this pass blends onto a cleared target, so it can't show the bug), the GENERAL layout used
   for the attachment, and the second pipeline/descriptor state.
5. Other observations:
   - 21 RGBA8 256x256 images (ids 881–963), sampled by the final composite and covering 7x3 tiles of the
     screen, are all zero in every capture and never written. Likely the page background layer; probably the
     same bug when their content was composed.
   - Images 6555/6559 with vertical stripes are the backdrop-blur chain (64-row strip scaled up), not damage.

## Suggested next steps

1. In replay, split the 6524 pass before draw 2 (insert `vkCmdEndRendering` + `vkCmdBeginRendering`
   with LOAD) and see if the masks then blend. If yes, the driver loses in-pass writes for blending
   (tile/GMEM or CCU issue), and a Zink workaround for `QUALCOMM_PROPRIETARY` with old driver versions could
   end/restart rendering before blended draws that overlap earlier draws, or use a barrier.
2. Edit the attachment layout from GENERAL to COLOR_ATTACHMENT_OPTIMAL (BeginRendering + barriers) in
   replay. Zink forces GENERAL for `VK_DRIVER_ID_QUALCOMM_PROPRIETARY` (`zink_screen.c:3175-3182`). Verify
   whether `ZINK_DEBUG=nogeneral` actually took effect in the live A/B (capture with it and check the
   layouts); it showed no change but wasn't confirmed.
3. Check the swapchain pass (46 src-over draws) per draw for any overlapping semi-transparent draw that
   blends correctly; if none do, dst reads are broken for every blended draw after the first.
4. Once the trigger is known, implement the workaround in the private Mesa/Zink build (needs the RedMagic
   build root) and drop or relax the software gate for the 740.

## How to reproduce the tooling

- **Env/args hooks (uncommitted, in the installed APK on the 8 Gen 2):**
  `tools/linuxfs/overlay/usr/local/bin/droiddeck-steam-taskset` exports `BL_STEAM_WEBHELPER_ENV`
  (space-separated `K=V`) and appends `BL_STEAM_WEBHELPER_ARGS` to the browser only. Set them with
  `droiddeckctl env set "BL_STEAM_CEF_SOFTWARE=0" "BL_STEAM_WEBHELPER_ENV=..."`.
- **RenderDoc capture of the browser (`scripts/rdoc-run.sh TAG rdoc`):** RenderDoc 1.46 aarch64 from
  `build/research/sparking-zero/gpu-tools/` is pushed to `/root/gpu-debug-tools`. RenderDoc must be an
  *implicit* layer: the manifest goes to `/root/.local/share/vulkan/implicit_layer.d/` and only the browser
  gets `ENABLE_VULKAN_RENDERDOC_CAPTURE=1`. Steam's bundled loader (`steamrtarm64/libvulkan.so.1`)
  ignores `VK_ADD_LAYER_PATH`. As an explicit layer, RenderDoc's pre-instance extension filter is skipped
  and Zink's `vkCreateInstance` fails. `scripts/rdoc-ctl.py N` triggers N-frame captures through
  RenderDoc's target control (ctypes).
- **Validation:** `scripts/rdoc-run.sh TAG vvl` (explicit layer with a full `VK_LAYER_PATH` is fine there).
- **Replay on the 740:** the driver does not honor `bufferDeviceAddressCaptureReplay` addresses, so
  convert to zip.xml (`renderdoccmd convert -c zip.xml`), run `scripts/rdoc-strip-bda.py` (zeroes opaque
  addresses, drops the capture-replay flag), convert back to `.rdc`. Then `scripts/rdoc-remote.sh CAP OUT [ids]`
  starts a session, runs `renderdoccmd remoteserver` in the guest (guest timeout max 600 s), forwards
  tcp:39920 over adb and runs `qrenderdoc.exe --python scripts/rdoc-replay.py` (Windows RenderDoc 1.46 in
  the session scratchpad; re-download from renderdoc.org if gone). `rdoc-replay.py` saves every pass/draw
  output; `rdoc-pixel.py` does pixel history and shader disassembly. Local replay on the PC's Intel Arc fails
  (`VK_EXT_queue_family_foreign` required). `capture/f4480nb.rdc` is already stripped and replayable.
- **Capture editing:** `rdoc-edit-blend.py` (blend factors / `blendEnable`), `rdoc-patch-ps.py`
  (SPIR-V patch of a pipeline's fragment shader), `rdoc-graph.py` (pass/target/sampled-image graph),
  `rdoc-init.py` (dumps images' starting contents to PNG).

## Gotchas

- Two Steam starts in a row that never show the UI trigger DroidDeck's auto-repair, which removes
  `package/*.installed` and re-extracts the client. Run a normal session between failing experiments.
- `rdoc-run.sh` deletes `/root/rdoc` on the phone at start (captures included).
- `qrenderdoc` adds adb forwards `localabstract:renderdoc_*` when it sees the phone; remove with
  `adb forward --remove-all` when done.
- Steam's `-cef-*` switches are applied in-process; `/proc/<pid>/cmdline` of the main browser process shows
  `--in-process-gpu`.

## Uncommitted work related to this

`droiddeck-session` (zero-copy probe + Zink < 4.0 browser gate), `droiddeck-steam-taskset` (env/args hooks),
`droiddeck-qualcomm-caps`, WSI patch 0005, `runtime.json`, `SessionFiles.kt`, tests
(`test_qualcomm_present.py`, `test_qualcomm_caps.py`, `test_qualcomm_browser.py`), README. Nothing after
8962b4f6 is committed. `PERFORMANCE_AUDIT.md` and this file stay uncommitted.
