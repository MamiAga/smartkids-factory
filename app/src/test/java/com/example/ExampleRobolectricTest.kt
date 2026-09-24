package com.example

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [36])
class ExampleRobolectricTest {

  @Test
  fun `read string from context`() {
    val context = ApplicationProvider.getApplicationContext<Context>()
    val appName = context.getString(R.string.app_name)
    assertEquals("SmartKids Network", appName)
  }

  @Test
  fun `verify automation control default state and toggling`() {
    val context = ApplicationProvider.getApplicationContext<Context>()
    val db = com.example.data.local.SmartKidsDatabase.getDatabase(context)
    val dao = db.automationControlDao()

    kotlinx.coroutines.runBlocking {
      val defaultControl = com.example.data.local.AutomationControlEntity(
        id = 1,
        enabled = false,
        dailyMasterEpisodes = 1,
        scheduleTime = "04:00",
        timezone = "Europe/Istanbul",
        activeLanguagesJson = "[\"EN\"]",
        lastHeartbeat = System.currentTimeMillis()
      )
      dao.insertOrUpdate(defaultControl)

      val fetched = dao.getControlSnapshot()
      org.junit.Assert.assertNotNull(fetched)
      org.junit.Assert.assertFalse(fetched!!.enabled)
      assertEquals(1, fetched.dailyMasterEpisodes)

      // Toggle to true
      dao.setEnabled(true)
      val enabledSnapshot = dao.getControlSnapshot()
      org.junit.Assert.assertNotNull(enabledSnapshot)
      org.junit.Assert.assertTrue(enabledSnapshot!!.enabled)

      // Toggle back to false (Paused)
      dao.setEnabled(false)
      val pausedSnapshot = dao.getControlSnapshot()
      org.junit.Assert.assertNotNull(pausedSnapshot)
      org.junit.Assert.assertFalse(pausedSnapshot!!.enabled)
    }
  }
}
