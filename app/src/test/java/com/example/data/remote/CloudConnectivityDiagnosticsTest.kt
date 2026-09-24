package com.example.data.remote

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class CloudConnectivityDiagnosticsTest {

    @Test
    fun testDiagnosticsRunsAndReturnsResults() {
        val diagnostics = CloudConnectivityDiagnostics()
        assertNotNull(diagnostics)

        runBlocking {
            val result = diagnostics.runFullDiagnostics()
            assertNotNull(result)
            assertTrue(result.results.isNotEmpty())
            println("Full Diagnostics Test Result: ${result.summaryMessage}")
            for (res in result.results) {
                println(" - Service: ${res.serviceName} | Status: ${res.status} | Latency: ${res.latencyMs}ms | Msg: ${res.message}")
            }
        }
    }
}
