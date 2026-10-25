# Deep Impact performance implementation report

Date: 2026-10-25. Target: the local `.xr` build, based on `prop-a750` at
`f6a2fbbe`. Branch: `deep-impact`. The separate official application was not
modified. The existing Adreno 740 fixes and Qualcomm shader compatibility policy
are retained.

## Result and scope

The changes remove avoidable BC tracking, pipeline recompilation, and SHM
allocation work. They preserve full SHM pixel uploads, synchronization, Steam's
browser workaround, touch controls, Mangoapp, and the selected graphics settings.
They do not remove rendering passes or change game quality to obtain a gain.

Validation is specific to the connected RedMagic 11 Pro / NX809J, Adreno 840,
Android 16, and proprietary Qualcomm **0.891.7** selected through
`qualcomm-adrenotools:v891.7`. This differs from the official-app re-audit's
891.11. Results from those two driver versions must not be combined as one A/B.
No test can establish that every game, driver, and phone is regression-free.

## Changes, in implementation order

| Commit | Change | Validation and remaining limits |
|---|---|---|
| `81bf2616` | Probe native BC support before the session; disable emulation tracking only when every exposed GPU has `textureCompressionBC` and sampled optimal support for all 16 BC formats. | Tests cover every queried format/device, missing feature, empty device lists, enumeration failure, and refusing emulated capabilities. Real GPU fill/readback and rendered cube passed. Explicit user policy is preserved; probe failure/timeout retains the previous default. |
| `8eae6e0a` | Canonicalize precompile/render pipeline keys, remove irrelevant blur specialization fields, reject impossible YCbCr masks, and release a pipeline when cancellation prevents insertion. | Native build and rendered cube/overlay passed. Color/output specialization remains part of the key; this does not precompile every runtime variant. |
| `45844de9` | Add a persistent Vulkan pipeline cache with driver/shader identity, bounded input size, integrity checks, and atomic replacement. | Cold, warm, deliberately corrupted, and recovered cache runs passed. Invalid cache input is ignored. Empty-cache and unavailable-cache fallbacks remain. |
| `45fff4da` | Reuse a coherently mapped SHM upload allocation up to 16 MiB. Larger uploads use temporary allocations. | Repeated rendered sessions passed. Full memcpy and the original GPU submit/wait remain; a mutex protects reuse. |
| `bd6c6fa1` | Reuse SHM texture snapshots after commit, GPU, and other references retire. | Standalone ARM64 C++ lifetime/budget tests passed; live reuse was observed. Pool is limited to eight textures / 16 MiB, Vulkan swapchain backends, and textures without a backend framebuffer. Busy/oversized cases allocate normally. |
| `ebcd900e` | Bind the uploaded constant-data size as the uniform descriptor range. | Native build/render passed; validation error `00332` disappeared. This fixes the invalid oversized descriptor without changing its contents. |
| `7de99f23` | Use the successful Qualcomm presentation probe for native games launched through the Steam FEX compatibility wrapper. | Visible Vulkan/XCB and OpenGL/Zink probes passed through this exact launch action. Per-game configuration is applied first; explicit SHM, failed probe, and non-Qualcomm paths keep the previous policy. Ordinary program/browser launches and metadata queries retain their environment. |

The source patches are `0131` through `0135` in `gamescope-patches/`. The rebuilt
private Gamescope and matching source archive are pinned in `runtime.json`.
The private binary SHA-256 is
`736d9723ff946452e1e884b8c7b284ee8d9f6705da97f3a0fb939caaf926845b`;
the corresponding source archive SHA-256 is
`1b2fefa1bcb1a1ab25ce585782b2ef3cbe5111303cee754d8d704dab148617ba`.

### Cache behavior

The filename includes vendor ID, device ID, driver version, pipeline-cache UUID,
and a hash of the selected shader bytes. The loader checks the custom payload
size/checksum and Vulkan cache header identity before handing bytes to the
driver. The maximum accepted payload is 64 MiB. Files live under the session's
private `XDG_CACHE_HOME/gamescope/pipelines` or `$HOME/.cache/gamescope/pipelines`.

Pipeline creation retains the driver's normal internally synchronized cache
behavior. Concurrent creation uses a shared application lock; snapshots use an
exclusive lock. See the Vulkan requirements for
[pipeline creation](https://docs.vulkan.org/refpages/latest/refpages/source/vkCreateComputePipelines.html)
and [cache snapshots](https://docs.vulkan.org/refpages/latest/refpages/source/vkGetPipelineCacheData.html).
The snapshot is saved after precompilation completes or is cancelled. Later
runtime-only variants are not guaranteed to be persisted by that snapshot.

## Measured gains

### Repeated pipeline precompilation

| Condition | Precompilation elapsed time |
|---|---:|
| New code, cold application cache | 12.414 s |
| Warm cache | 0.032 s |
| Warm cache after final synchronization implementation | 0.038 s |
| Deliberately damaged cache, rejected and regenerated | 12.422 s |

This is approximately **99.7% less repeated precompilation time**. The measured
first cube frame remained approximately 4.7 seconds. It is not a 99.7% reduction
in application startup, game loading, or frame time. The saved payload was
1,748,238 bytes on this driver.

### BC tracking microbenchmark

An ABBA comparison on 891.7 measured median CPU time for recorded command calls:

| Command-buffer population | Default tracking, mean of two medians | BC tracking disabled, mean of two medians | Reduction |
|---|---:|---:|---:|
| 1 | 822 ns | 714.5 ns | 13.1% |
| 64 | 873 ns | 731 ns | 16.3% |
| 1024 | 1911.5 ns | 741 ns | 61.2% |

These measurements include Python/ctypes overhead and describe this dispatch
microbenchmark. They are **not gameplay FPS percentages**. A separate run with
the automatic policy confirmed `HYBRIS_BC_TEXTURES=0` and correct GPU readback.

### Sparking! ZERO

The heavy-game validation uses Steam app `1790600`, ARM64 Experimental Compatible
Proton, and `-dx11`. The updated renderer reached the title screen, animated 3D
main menu, and an actual City combat scene with Goku/Frieza, effects, HUD, touch
controls, and the performance overlay visible. The combat capture is a functional
test: its changing action and introductory effects do not provide a matched
before/after benchmark. Isaac is not used to support a heavy-game performance
claim.

The controlled comparison holds the Battle & Training menu with Super Training
highlighted, showing Gohan and Piccolo. Each group contains three eight-second
CPU windows; 1.0 core means one fully occupied CPU core. Run order is updated,
baseline, then updated again. The Android SurfaceFlinger window is approximately 9.7 seconds due
to collection overhead. Resolution remains 1590 × 720; both compared sessions use
the same forced SHM path and `PROTON_LOG=1`. The baseline uses the original
private Gamescope and `HYBRIS_BC_TEXTURES=missing`; the updated session uses the
new renderer and automatic BC policy. This isolates the safe changes while
holding the presentation route constant.

| Measurement, mean of three windows | Original renderer | Updated, first run | Updated, repeat launch |
|---|---:|---:|---:|
| Gamescope CPU, cores | 0.2794 | 0.1293 | 0.1718 |
| Game process CPU, cores | 3.6604 | 3.5403 | 3.5210 |
| Android surface presentations/s, approximate | 33.04 | 37.46 | 39.66 |
| GPU temperature at window starts | 71.8–74.1 °C | 73.7–74.5 °C | 72.9–75.7 °C |

Gamescope CPU use fell **53.7%** in the first run and **38.5%** in the repeat.
Android presentation rate rose **13.4%** and **20.0%**, respectively. These are
short fixed-menu observations, not a prediction of combat FPS. The game process
still dominates CPU use. The settings file's SHA-256 was identical between the
baseline and repeated updated menu runs:
`084694ff6e803344a565e1b9f23c57902ecadd06a3dd4e7083b5653e766f4673`.
Session preference values also matched the initial snapshot exactly after these
tests.

SurfaceFlinger counts Android surface presentations, which can include overlay
updates or repeated game content. Its rate must not be reported as engine FPS.
The instantaneous Mangoapp readout is also insufficient to establish average
combat FPS or 1% lows. Short CPU measurements are affected by thermal state and
clock policy; the repeated updated run checks whether the first result survives
another game launch. Loading periods are excluded: the black startup screen
eventually advanced on the original renderer as well.

## Verification

The implementation was built and exercised one change at a time, using the
intermediate binaries saved in the local evidence directory. Cache tests include
empty, warm, corrupted, and recovery cases. The texture-pool C++ test covers
commit/GPU/private references, immutable old snapshots, format/dimension
mismatch, oversize input, busy budget fallback, idle eviction, and object cleanup.

Synchronization validation found no `SYNC-HAZARD` in the tested SHM pool runs.
The uniform-range fix removes `VUID-VkWriteDescriptorSet-descriptorType-00332`.
Validation is **not clean**: `12205` (YCbCr shader indexing), `09506` (null image
view), `09600` (sampled-image layout), and the storage-image format mismatch
warning remain. Earlier game-side WSI findings concerning maintenance extensions,
present modes, and surface lifetime are not claimed fixed by this work.

The selected Android driver tests passed: nine tests across
`QualcommSystemDriverTest` and `QualcommDriverPackageTest`. Runtime inputs and the
APK are checked using `tools/release/runtime_inputs.py` and
`tools/release/check_session_assets.py`. The APK is assembled with the prepared
runtime assets and all five add-on packs' valid checksums, supporting the normal
fresh-install runtime setup. Installed-device runtime reuse is not used.

The 23 Qualcomm Python tests passed on Windows with Git Bash available on PATH.
The existing FEX launcher suite plus the new presentation policy tests also ran
inside ARM64 Linux with its real `fcntl` module: **53 tests passed**. The two
counts overlap by the three new policy tests and must not be added as unique
tests. An initial Windows run without Bash failed to find the shell; rerunning
with the required tool on PATH passed.

The native launch probes used one renderer at a time. The cube selected Adreno
840 / 891.7 and logged a Gamescope WSI swapchain with `flip: true`. The OpenGL
probe visibly rendered its gears and reported Zink, OpenGL 4.6 Compatibility,
and Mesa 26.2.3 through the same WSI. These are ARM64 probe applications through
the Steam compatibility action, not coverage of all x86 Linux games under FEX.
The caller kept both SHM compatibility variables. No browser launch policy was
changed.

The upscaler smoke test used an actual **640 × 360** X11 client and **1590 × 720**
output. SHM staging retained 921,600 bytes, confirming the smaller input rather
than an ineffective resize request. Linear, nearest, FSR, NIS, and SGSR selections
all kept the cube rendering and the session healthy. This checks basic rendering
and switching; it is not pixel-exact reference-image conformance.

The local worktree contains the build and evidence, while the original checkout
is preserved. Test binaries and session overrides are temporary; the final
delivery uses the packaged renderer. Runtime/game settings and QoL features are
not traded away for the measured savings.

After clearing every diagnostic environment/binary override, Sparking! ZERO
also reached its animated main menu on the normal Qualcomm presentation path.
The session reported automatic BC policy `0`, a successful zero-copy capability
probe, and the game's Gamescope WSI swapchain with `flip: true`. Neither forced
SHM nor Proton logging was active in this final functional run. The controlled
table above remains the SHM comparison; this final run is not mixed into it.

## Excluded experiments and remaining research

An additional glslang `-Os` experiment did not eliminate validation `12205` and
grew the private binary from roughly 3.62 to 5.46 MB. It was reverted and is not
part of the pinned source/binary.

The following remain separate research work because their correctness depends
on ownership, fences, damage history, or broader device/game coverage:

- Asynchronous SHM uploads and combining upload/composition submissions. Current
  work deliberately retains the full copy and wait.
- Damage-only uploads and cropping Mangoapp. Full buffer refresh and overlay
  functionality are retained.
- Direct Android hardware-buffer presentation and removal of a compositor pass.
  No release-fence or frame-callback behavior was changed.
- Broad changes to present threading/vblank, global driver features, or DXVK
  submission heuristics. Submission microbenchmarks do not establish a safe
  universal game setting.
- Remaining validation findings, HDR/VR, other phone/driver combinations, and
  long combat frametime runs. These require additional targeted validation.

## Reproducing and evidence

Start with the existing runtime preparation documented in `README.md`, then:

```powershell
python -m unittest discover -s tools/tests -p 'test_qualcomm*.py'
python tools/release/runtime_inputs.py verify
./gradlew.bat -PskipRust=true :app:assembleDebug --console=plain
python tools/release/runtime_inputs.py apk app/build/outputs/apk/debug/app-debug.apk
python tools/release/check_session_assets.py app/build/outputs/apk/debug/app-debug.apk
```

On ARM64 Linux, the pool test can be compiled against the prepared Gamescope
source's `src` directory:

```sh
c++ -std=c++20 -Wall -Wextra -Werror -I/path/to/gamescope/src \
    tools/qualcomm/shm_texture_pool_test.cpp -o /tmp/shm-pool-test
/tmp/shm-pool-test
PYTHONPATH=tools/tests python3 -m unittest test_droiddeck_fex test_qualcomm_native_present
```

For a Qualcomm session, logs report the automatic BC decision, pipeline-cache
load/save, precompilation duration, retained SHM staging size, and first idle
texture reuse. An explicit `HYBRIS_BC_TEXTURES` value takes precedence over the
new automatic gate. `BL_QUALCOMM_SHM=1` retains the SHM diagnostic/fallback route.

Raw logs, screenshots, microbenchmark JSON, controlled samples, test outputs,
and intermediate binaries are retained locally under the ignored
`build/deep-impact/` directory in this worktree. That evidence is not uploaded
with the source branch because it can contain local Steam/session information.
The earlier audits remain in the original checkout under
`C:/Users/kimchi/Desktop/droiddeck/tools/qualcomm/`.
