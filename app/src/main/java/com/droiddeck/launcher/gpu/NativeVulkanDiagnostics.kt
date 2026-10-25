package com.droiddeck.launcher.gpu

import android.content.Context
import android.os.SystemClock
import android.util.Log
import org.json.JSONObject
import java.io.File
import java.util.concurrent.TimeUnit

object NativeVulkanDiagnostics {
    fun run(context: Context, directory: File, keepRunning: () -> Boolean) {
        val output = File(directory, "vulkan-native.log")
        val executable = File(context.applicationInfo.nativeLibraryDir, "liba850vulkanprobe.so")
        val cases = listOf("platform" to "0", "platform" to "3",
            "hal-version" to "0", "hal-version-after-loader" to "0")
        try {
            output.writeText(JSONObject().put("event", "native.diagnostics.start").put("schema", 2)
                .put("uid", android.os.Process.myUid()).put("app_vulkan", JSONObject(VulkanInfo.query()))
                .toString() + "\n")
            for ((mode, minor) in cases) {
                if (!keepRunning()) break
                val started = SystemClock.elapsedRealtime()
                var process: Process? = null
                val status = try {
                    val builder = ProcessBuilder(executable.path, mode, minor,
                        context.applicationInfo.targetSdkVersion.toString())
                        .directory(context.filesDir).redirectErrorStream(true)
                        .redirectOutput(ProcessBuilder.Redirect.appendTo(output))
                    builder.environment().keys.removeAll { it.startsWith("LD_") || it.startsWith("VK_") ||
                        it.startsWith("HYBRIS_") || it.startsWith("PROOT_") || it == "GLIBC_TUNABLES" }
                    process = builder.start()
                    val deadline = started + 4_000
                    while (keepRunning() && SystemClock.elapsedRealtime() < deadline &&
                        !process.waitFor(100, TimeUnit.MILLISECONDS)) { }
                    if (process.isAlive) {
                        process.destroyForcibly()
                        process.waitFor(1, TimeUnit.SECONDS)
                        if (keepRunning()) "timeout" else "cancelled"
                    } else process.exitValue().toString()
                } catch (error: Exception) {
                    output.appendText(JSONObject().put("event", "native.probe.error")
                        .put("error", error.toString()).toString() + "\n")
                    "error"
                } finally {
                    process?.takeIf { it.isAlive }?.destroyForcibly()
                }
                output.appendText(JSONObject().put("event", "native.probe.complete")
                    .put("mode", mode).put("minor", minor).put("status", status)
                    .put("elapsed_ms", SystemClock.elapsedRealtime() - started).toString() + "\n")
            }
            output.appendText(JSONObject().put("event", "native.diagnostics.complete").toString() + "\n")
        } catch (error: Exception) {
            Log.w("NativeVulkanDiagnostics", "native Vulkan diagnostics", error)
        }
    }
}
