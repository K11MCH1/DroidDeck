# Adreno 850 Vulkan startup diagnostics

This branch investigates the OnePlus PYB110 / Android 17 / Adreno850v2 startup
failure where the bridged Android `vkCreateInstance` returns `1` and Gamescope
subsequently reports `VK_ERROR_INCOMPATIBLE_DRIVER`. It retains the pinned
Qualcomm bridge, Gamescope, WSI and Mesa versions.

## Device owner

1. Install the diagnostic APK as an update to the existing test-key build.
   This APK uses the repository's test signing key. If Android rejects the
   signature, retain the installed app and report the installer error.
2. Keep the original failing configuration: system Android display driver and
   **System Qualcomm driver** as the Linux runtime driver. Fully close and
   reopen DroidDeck after installation.
3. Launch Steam once. The isolated probes can add up to 45 seconds before
   Gamescope starts. Let the launch finish or return its failure message.
4. Use **Share logs** and return the complete ZIP. It should contain
   `vulkan-diagnostics.log`, `session.log`, `app.log`, `device.txt` and
   `events.jsonl` for the same launch.

No game launch or Steam sign-in is required to reproduce this initialization
failure. An existing runtime can be reused; the APK also carries the verified
runtime assets and add-on pack identities required for a fresh installation.

## Captured evidence

The JSON-lines diagnostic report records the selected manifests, an allowlist
of graphics environment variables, and SHA-256 identities for the Android
Vulkan loader and selected vendor HAL. Each probe runs in a fresh process with
a four-second timeout; the session supervisor limits the entire probe stage
to 45 seconds and proceeds to Gamescope even when a probe fails.

- Linux Vulkan loader: API 1.0, 1.3 and 1.4 with no requested extensions.
- Linux Vulkan loader: API 1.3 with Wayland surface extensions, with the session
  layers enabled and again with explicit and implicit layers disabled.
- Direct bridge ICD: API 1.0 and 1.3, bypassing the Linux Vulkan loader.
- Android Vulkan loader through libhybris: API 1.0 and 1.3, bypassing the bridge
  ICD and Linux Vulkan loader.

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
./gradlew -PskipRust=true :app:testDebugUnitTest \
  --tests 'com.droiddeck.launcher.gpu.QualcommSystemDriverTest' \
  --tests 'com.droiddeck.launcher.gpu.QualcommDriverPackageTest'
python tools/release/runtime_inputs.py apk /path/to/diagnostic.apk
python tools/release/check_session_assets.py /path/to/diagnostic.apk
```

The native test verifies that logging forwards the original request and
allocator and preserves both the positive `VK_NOT_READY` result and the
negative `VK_ERROR_INCOMPATIBLE_DRIVER` result. Host tests and package
verification do not establish Vulkan startup success on the affected phone.
