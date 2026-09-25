// Suppress benign KSP IntelliJ decompiler teardown race condition on AWT-EventQueue thread
val prevHandler = Thread.getDefaultUncaughtExceptionHandler()
Thread.setDefaultUncaughtExceptionHandler { t, e ->
  val isKspAwtNpe = t.name.startsWith("AWT-EventQueue") &&
    generateSequence(e) { it.cause }.any { ex ->
      ex is NullPointerException && ex.stackTrace.any { frame ->
        frame.className.contains("ksp.com.intellij") || frame.className.contains("com.intellij")
      }
    }
  if (!isKspAwtNpe) {
    prevHandler?.uncaughtException(t, e)
  }
}

pluginManagement {
  repositories {
    google {
      content {
        includeGroupByRegex("com\\.android.*")
        includeGroupByRegex("com\\.google.*")
        includeGroupByRegex("androidx.*")
      }
    }
    mavenCentral()
    gradlePluginPortal()
  }
}

plugins { id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0" }

dependencyResolutionManagement {
  repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
  repositories {
    google()
    mavenCentral()
  }
}

rootProject.name = "SmartKids Network"

include(":app")
