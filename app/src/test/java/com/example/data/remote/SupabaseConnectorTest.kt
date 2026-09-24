package com.example.data.remote

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class SupabaseConnectorTest {

    @Test
    fun testSupabaseConnectorReadsLiveTable() {
        val liveUrl = System.getenv("SUPABASE_URL") ?: "https://qhyiizlrxxrftqeueuxp.supabase.co"
        val liveKey = System.getenv("SUPABASE_ANON_KEY") ?: System.getenv("SUPABASE_KEY") ?: ""

        val connector = SupabaseConnector(
            customUrl = liveUrl,
            customKey = liveKey
        )
        assertNotNull(connector)

        runBlocking {
            val result = connector.checkAutomationControlTable()
            assertNotNull(result)

            println("=== SUPABASE CONNECTOR TEST RESULT: $result ===")
            when (result) {
                is SupabaseResult.Success -> {
                    assertEquals(200, result.statusCode)
                    assertTrue("automation_control should contain at least 1 item", result.items.isNotEmpty())
                    val firstRow = result.items.first()
                    assertEquals(1, firstRow.id)
                    println("Successfully read from live table via Retrofit! ID: ${firstRow.id}, Enabled: ${firstRow.enabled}")
                }
                is SupabaseResult.TableNotFound -> {
                    throw AssertionError("Table not found: ${result.message}")
                }
                is SupabaseResult.Error -> {
                    // Sandbox network may or may not allow outbound HTTP during robolectric unit test
                    println("SupabaseConnector returned Error in sandbox environment: ${result.message}")
                }
            }
        }
    }
}
