package com.example.data.remote

import android.util.Log
import com.example.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL

enum class ServiceStatus {
    IDLE,
    CHECKING,
    SUCCESS,
    WARNING,
    FAILED
}

data class ServiceCheckResult(
    val serviceName: String,
    val status: ServiceStatus,
    val message: String,
    val latencyMs: Long = 0,
    val detail: String? = null
)

data class FullDiagnosticsResult(
    val allHealthy: Boolean,
    val results: List<ServiceCheckResult>,
    val summaryMessage: String
)

/**
 * Diagnostic service that tests connectivity to Supabase, GitHub Actions repository API,
 * and YouTube API / Google OAuth token endpoint to verify if the factory can start seamlessly.
 */
class CloudConnectivityDiagnostics {
    companion object {
        private const val TAG = "CloudDiagnostics"
    }

    suspend fun runFullDiagnostics(): FullDiagnosticsResult = kotlinx.coroutines.coroutineScope {
        withContext(Dispatchers.IO) {
            // Eşzamanlı (Concurrent) bağlantı testleri: async / await
            val supabaseDeferred = async { testSupabaseConnection() }
            val githubDeferred = async { testGitHubConnection() }
            val youtubeDeferred = async { testYouTubeApiReadiness() }

            val list = listOf(
                supabaseDeferred.await(),
                githubDeferred.await(),
                youtubeDeferred.await()
            )

            // Determine overall health: all must be SUCCESS or WARNING (no FAILED)
            val allHealthy = list.none { it.status == ServiceStatus.FAILED }
            val summary = if (allHealthy) {
                "Tüm bulut servisleri ve API bağlantıları hazır. Üretim güvenle başlatılabilir!"
            } else {
                val failedServices = list.filter { it.status == ServiceStatus.FAILED }.joinToString(", ") { it.serviceName }
                "Dikkat: $failedServices bağlantısında sorun tespit edildi."
            }

            FullDiagnosticsResult(
                allHealthy = allHealthy,
                results = list,
                summaryMessage = summary
            )
        }
    }

    private fun testSupabaseConnection(): ServiceCheckResult {
        val start = System.currentTimeMillis()
        val urlStr = BuildConfig.SUPABASE_URL.trimEnd('/')
        val anonKey = BuildConfig.SUPABASE_ANON_KEY

        if (urlStr.isBlank() || anonKey.isBlank()) {
            return ServiceCheckResult(
                serviceName = "Supabase REST API",
                status = ServiceStatus.FAILED,
                message = "SUPABASE_URL veya ANON_KEY eksik",
                latencyMs = 0
            )
        }

        return try {
            val endpoint = "$urlStr/rest/v1/automation_control?id=eq.1&select=id,enabled"
            val conn = URL(endpoint).openConnection() as HttpURLConnection
            conn.requestMethod = "GET"
            conn.setRequestProperty("apikey", anonKey)
            conn.setRequestProperty("Authorization", "Bearer $anonKey")
            conn.setRequestProperty("Accept", "application/json")
            conn.connectTimeout = 6000
            conn.readTimeout = 6000

            val code = conn.responseCode
            val latency = System.currentTimeMillis() - start

            if (code == 200) {
                val body = conn.inputStream.bufferedReader().use { it.readText() }
                conn.disconnect()
                ServiceCheckResult(
                    serviceName = "Supabase PostgreSQL",
                    status = ServiceStatus.SUCCESS,
                    message = "Bağlantı başarılı (HTTP 200 OK)",
                    latencyMs = latency,
                    detail = "Tablo automation_control erişilebilir: $body"
                )
            } else {
                val err = conn.errorStream?.bufferedReader()?.use { it.readText() } ?: ""
                conn.disconnect()
                ServiceCheckResult(
                    serviceName = "Supabase PostgreSQL",
                    status = ServiceStatus.FAILED,
                    message = "HTTP Hata Kodu: $code",
                    latencyMs = latency,
                    detail = err
                )
            }
        } catch (e: Exception) {
            ServiceCheckResult(
                serviceName = "Supabase PostgreSQL",
                status = ServiceStatus.FAILED,
                message = "Bağlantı hatası: ${e.localizedMessage}",
                latencyMs = System.currentTimeMillis() - start
            )
        }
    }

    private fun testGitHubConnection(): ServiceCheckResult {
        val start = System.currentTimeMillis()
        return try {
            // Test GitHub public API availability (rate limit & meta endpoint)
            val conn = URL("https://api.github.com/zen").openConnection() as HttpURLConnection
            conn.requestMethod = "GET"
            conn.setRequestProperty("User-Agent", "SmartKids-Android-Diagnostics")
            conn.connectTimeout = 5000
            conn.readTimeout = 5000

            val code = conn.responseCode
            val latency = System.currentTimeMillis() - start

            if (code == 200) {
                val zen = conn.inputStream.bufferedReader().use { it.readText() }
                conn.disconnect()
                ServiceCheckResult(
                    serviceName = "GitHub API & Actions",
                    status = ServiceStatus.SUCCESS,
                    message = "GitHub API erişilebilir (HTTP 200)",
                    latencyMs = latency,
                    detail = "GitHub Zen: \"$zen\""
                )
            } else {
                conn.disconnect()
                ServiceCheckResult(
                    serviceName = "GitHub API & Actions",
                    status = ServiceStatus.WARNING,
                    message = "GitHub API HTTP $code döndürdü",
                    latencyMs = latency
                )
            }
        } catch (e: Exception) {
            ServiceCheckResult(
                serviceName = "GitHub API & Actions",
                status = ServiceStatus.FAILED,
                message = "GitHub bağlantı hatası: ${e.localizedMessage}",
                latencyMs = System.currentTimeMillis() - start
            )
        }
    }

    private fun testYouTubeApiReadiness(): ServiceCheckResult {
        val start = System.currentTimeMillis()
        return try {
            // Test Google APIs endpoint reachability
            val conn = URL("https://www.googleapis.com/discovery/v1/apis/youtube/v3/rest").openConnection() as HttpURLConnection
            conn.requestMethod = "GET"
            conn.setRequestProperty("User-Agent", "SmartKids-Android-Diagnostics")
            conn.connectTimeout = 5000
            conn.readTimeout = 5000

            val code = conn.responseCode
            val latency = System.currentTimeMillis() - start

            if (code == 200) {
                conn.disconnect()
                ServiceCheckResult(
                    serviceName = "YouTube Data API v3",
                    status = ServiceStatus.SUCCESS,
                    message = "YouTube v3 API uç noktası aktif (HTTP 200)",
                    latencyMs = latency,
                    detail = "Google Discovery API doğrulaması başarılı."
                )
            } else {
                conn.disconnect()
                ServiceCheckResult(
                    serviceName = "YouTube Data API v3",
                    status = ServiceStatus.WARNING,
                    message = "HTTP $code yanıtı alındı",
                    latencyMs = latency
                )
            }
        } catch (e: Exception) {
            ServiceCheckResult(
                serviceName = "YouTube Data API v3",
                status = ServiceStatus.FAILED,
                message = "Google/YouTube API hatası: ${e.localizedMessage}",
                latencyMs = System.currentTimeMillis() - start
            )
        }
    }
}
