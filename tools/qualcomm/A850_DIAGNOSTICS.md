# Adreno 850 Vulkan startup diagnostics v2

This branch investigates the OnePlus PYB110 / Android 17 / Adreno850v2 startup
failure where the bridged Android `vkCreateInstance` returns `1` and Gamescope
subsequently reports `VK_ERROR_INCOMPATIBLE_DRIVER`. It retains the pinned
Qualcomm bridge, Gamescope, WSI and Mesa versions.

## Device owner

1. Install v2 of **DroidDeck A850 Diagnostics** (`com.droiddeck.launcher.a850`). It
   installs alongside the official app with separate app data and uses the
   repository's test signing key. Install it over v1 to preserve its runtime
   and settings. Version code 16 permits an ordinary update from v1 (15).
2. Install the runtime if this is a fresh installation, and select the original failing
   configuration: system Android display driver and **System Qualcomm driver**
   as the Linux runtime driver. Fully close and reopen the diagnostic app.
3. Launch Steam once. The isolated probes can add up to 60 seconds before
   Gamescope starts. Let the launch finish or return its failure message.
4. Use **Share logs** and return the complete ZIP. It should contain
   `vulkan-native.log`, `vulkan-diagnostics.log`, `session.log`, `app.log`, `device.txt` and
   `events.jsonl` for the same launch.

No game launch or Steam sign-in is required to reproduce this initialization
failure. The APK carries the verified runtime assets and add-on pack identities
required for this separate installation. It cannot reuse the official app's
private runtime or settings.

## Captured evidence

V1 established that the HAL's version query returns `1` while writing Vulkan
1.4.0, and that even extension-free creation fails through the bridged Android
loader. V2 compares the same tracing C source in two execution environments:

- A Bionic executable started directly by the Android app, outside PRoot and
  libhybris, under the app's UID. Its report is `vulkan-native.log`.
- A glibc shared library called inside PRoot with libhybris's own open, symbol,
  address and loader-error functions. Its report is `vulkan-diagnostics.log`.

Both environments test extension-free Android-loader instance creation at API
1.0 and 1.3. Both resolve the vendor HAL's version entry point through its
`GetInstanceProcAddr` callback and through an exported symbol when available.
The version query records its unmodified return code, the initial output
sentinel, whether the output was written, and the reported version. HAL queries
are compared before and after initializing the Android loader's public version
query, in separate disposable processes.

Each resolved function records its address, owning module, module-relative
offset and symbol name when available. The raw HAL module/device ABI is checked
before reading its entry points. Unknown-command lookup is recorded without
calling the resulting pointer. The probes retain the HAL until process exit
and create instances only through the Android loader.

The native executable logs the effective target SDK when the linker exposes
that query, and attempts to use the app's target SDK when the setter is available.
An Android executable lacks the app's Java/GraphicsEnv initialization. The
report includes the app's cached in-process Vulkan information to make that
context difference visible. A native HAL load can be refused by Android's
linker namespaces; that failure is reported rather than bypassed. Native
controls always use the phone's system driver, so select System Qualcomm for
the bridged cases too.

The JSON-lines guest diagnostic report also records the selected manifests, an allowlist
of graphics environment variables, and SHA-256 identities for the Android
Vulkan loader and selected vendor HAL. Each probe runs in a fresh process with
a four-second timeout. Four native cases precede the guest launch. The guest
supervisor limits its probe stage to 35 seconds and proceeds to Gamescope even
when a probe fails. Cancellation stops the native probe process.

- Linux Vulkan loader: API 1.3 without extensions, with the session layers.
- Linux Vulkan loader: API 1.3 with Wayland surface extensions and all layers disabled.
- Direct bridge ICD: API 1.3, bypassing the Linux Vulkan loader.
- Shared C traces: API 1.0/1.3 Android-loader creation and the two HAL version-query cases.

The direct Android cases still use libhybris and the session's PRoot mounts;
they are not native Android-process control measurements. All cases preserve
the selected driver and run before Steam starts. They create and destroy an
instance without starting a GPU workload.

The existing shader layer logs Gamescope's actual requested Vulkan version,
extension/layer names, pNext structure types, allocator presence and downstream
return code to `session.log`. It forwards the request and return code unchanged.
Verbose Linux loader output identifies driver and layer selection. `app.log`
captures the app UID, including its native children, to include Android
loader/vendor messages the previous app-PID-only filter omitted. Android may
restrict which log entries an ordinary app can read.

The normal Share logs collection scrubs the new text report with the other
session artifacts. `DROIDDECK_VULKAN_DIAGNOSTICS=0` in a session environment
override skips the prelaunch probe stage.

## Local validation

```sh
python -m unittest discover -s tools/tests -p test_a850_vulkan_diagnostics.py -v
python -m unittest discover -s tools/tests -p 'test_qualcomm*.py' -v
cc -Wall -Wextra -Werror -I /path/to/Vulkan-Headers/include \
  tools/qualcomm/test_diagnostic_layer.c -o test-diagnostic-layer
DROIDDECK_VULKAN_DIAGNOSTICS=1 ./test-diagnostic-layer
cc -Wall -Wextra -Werror -I /path/to/Vulkan-Headers/include \
  tools/qualcomm/test_vulkan_trace.c -o test-vulkan-trace
A850_TRACE_TEST=./test-vulkan-trace python -m unittest discover \
  -s tools/tests -p test_a850_vulkan_diagnostics.py -v
./gradlew -PskipRust=true :app:testDebugUnitTest \
  --tests 'com.droiddeck.launcher.gpu.QualcommSystemDriverTest' \
  --tests 'com.droiddeck.launcher.gpu.QualcommDriverPackageTest'
python tools/release/runtime_inputs.py apk /path/to/diagnostic.apk
python tools/release/check_session_assets.py /path/to/diagnostic.apk
```

The native test verifies that logging forwards the original request and
allocator and preserves both the positive `VK_NOT_READY` result and the
negative `VK_ERROR_INCOMPATIBLE_DRIVER` result. Trace tests cover version-query
output and return preservation, initialization order, invalid-handle cleanup,
and JSON escaping. Package verification checks both tracing binaries against
their recorded source and output hashes. Host tests and package
verification do not establish Vulkan startup success on the affected phone.
