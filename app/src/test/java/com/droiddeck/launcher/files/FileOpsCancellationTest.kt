package com.droiddeck.launcher.files

import java.io.File
import java.util.concurrent.CancellationException
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class FileOpsCancellationTest {
    @get:Rule val tmp = TemporaryFolder()

    @Test fun cancellingCopyRemovesAnIncompleteNewFile() {
        val source = tmp.newFile("source").apply { writeBytes(ByteArray(5 * 1024 * 1024)) }
        val destination = File(tmp.root, "destination")

        assertThrows(CancellationException::class.java) {
            FileOps.copyWithProgress(source, destination, { _, _ -> throw CancellationException("cancel") })
        }

        assertTrue(source.exists())
        assertFalse(destination.exists())
    }

    @Test fun cancellingMoveFallbackPreservesTheSourceAndExistingDestination() {
        val source = tmp.newFile("source").apply { writeText("replacement") }
        val destination = tmp.newFile("destination").apply { writeText("original") }

        assertThrows(CancellationException::class.java) {
            FileOps.moveWithProgress(source, destination, { _, _ -> throw CancellationException("cancel") })
        }

        assertEquals("replacement", source.readText())
        assertEquals("original", destination.readText())
    }

    @Test fun cancellingRecursiveDeleteStopsBeforeTheNextFile() {
        val directory = tmp.newFolder("directory")
        repeat(3) { File(directory, "file-$it").writeText("content") }
        var checks = 0

        assertThrows(CancellationException::class.java) {
            FileOps.delete(directory) { ++checks > 3 }
        }

        assertTrue(directory.exists())
        assertEquals(2, directory.listFiles()?.size)
    }
}
