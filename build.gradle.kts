// Top-level build file where you can add configuration options common to all sub-projects/modules.
val defaultUncaughtHandler = Thread.getDefaultUncaughtExceptionHandler()
Thread.setDefaultUncaughtExceptionHandler { t, e ->
  val isKspAwtNpe = t.name.startsWith("AWT-EventQueue") &&
    generateSequence(e) { it.cause }.any { ex ->
      ex is NullPointerException && ex.stackTrace.any { frame ->
        frame.className.contains("ksp.com.intellij") || frame.className.contains("com.intellij")
      }
    }
  if (!isKspAwtNpe) {
    defaultUncaughtHandler?.uncaughtException(t, e)
  }
}

plugins {
  alias(libs.plugins.android.application) apply false
  alias(libs.plugins.kotlin.compose) apply false
  alias(libs.plugins.google.devtools.ksp) apply false
  alias(libs.plugins.roborazzi) apply false
  alias(libs.plugins.secrets) apply false
  alias(libs.plugins.google.services) apply false
}
