package com.example.data.remote

import android.util.Log
import com.example.BuildConfig
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.ResponseBody
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Query
import java.util.concurrent.TimeUnit

/**
 * Data model representing the structure of 'automation_control' table row in Supabase.
 */
@JsonClass(generateAdapter = true)
data class AutomationControlDto(
    @param:Json(name = "id") val id: Int = 1,
    @param:Json(name = "enabled") val enabled: Boolean = false,
    @param:Json(name = "daily_master_episodes") val dailyMasterEpisodes: Int? = 1,
    @param:Json(name = "schedule_time") val scheduleTime: String? = "04:00",
    @param:Json(name = "timezone") val timezone: String? = "Europe/Istanbul",
    @param:Json(name = "active_languages") val activeLanguages: Any? = null,
    @param:Json(name = "active_channels") val activeChannels: Any? = null,
    @param:Json(name = "generation_mode") val generationMode: String? = "AUTONOMOUS",
    @param:Json(name = "publish_mode") val publishMode: String? = "AUTO",
    @param:Json(name = "created_at") val createdAt: String? = null,
    @param:Json(name = "updated_at") val updatedAt: String? = null,
    @param:Json(name = "last_heartbeat") val lastHeartbeat: String? = null,
    @param:Json(name = "last_run_at") val lastRunAt: String? = null,
    @param:Json(name = "next_run_at") val nextRunAt: String? = null,
    @param:Json(name = "current_job_id") val currentJobId: String? = null,
    @param:Json(name = "failure_count") val failureCount: Int? = 0
)

/**
 * Retrofit API interface for Supabase PostgREST endpoints.
 */
interface SupabaseApiService {
    @GET("rest/v1/automation_control")
    suspend fun getAutomationControl(
        @Header("apikey") apiKey: String,
        @Header("Authorization") authorization: String,
        @Query("select") select: String = "*",
        @Query("id") idFilter: String? = null
    ): Response<List<AutomationControlDto>>

    @GET("rest/v1/automation_control")
    suspend fun getAutomationControlRaw(
        @Header("apikey") apiKey: String,
        @Header("Authorization") authorization: String,
        @Query("select") select: String = "*"
    ): Response<ResponseBody>
}

/**
 * Result state sealed class for Supabase connection verification.
 */
sealed class SupabaseResult {
    data class Success(val statusCode: Int, val items: List<AutomationControlDto>, val rawJson: String) : SupabaseResult()
    data class TableNotFound(val statusCode: Int, val errorCode: String, val message: String) : SupabaseResult()
    data class Error(val statusCode: Int?, val message: String, val rawErrorBody: String?) : SupabaseResult()
}

/**
 * Kotlin connector class using Retrofit to communicate with Supabase,
 * verify connectivity and table structure, and specifically intercept PGRST205 / 404 errors.
 */
class SupabaseConnector(
    private val customUrl: String? = null,
    private val customKey: String? = null
) {
    companion object {
        private const val TAG = "SupabaseConnector"
    }

    private val baseUrl: String = (customUrl ?: BuildConfig.SUPABASE_URL).trimEnd('/') + "/"
    private val apiKey: String = customKey ?: BuildConfig.SUPABASE_ANON_KEY

    private val moshi: Moshi = Moshi.Builder()
        .addLast(KotlinJsonAdapterFactory())
        .build()

    private val okHttpClient: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .addInterceptor(HttpLoggingInterceptor { message ->
            Log.d(TAG, "OkHttp: $message")
        }.apply {
            level = HttpLoggingInterceptor.Level.BODY
        })
        .build()

    private val apiService: SupabaseApiService by lazy {
        Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(okHttpClient)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
            .create(SupabaseApiService::class.java)
    }

    /**
     * Executes GET request to 'automation_control' table,
     * logs status, headers, and body, and catches PGRST205 / 404 specifically.
     */
    suspend fun checkAutomationControlTable(): SupabaseResult = withContext(Dispatchers.IO) {
        Log.i(TAG, "==================================================")
        Log.i(TAG, "Starting Supabase Connectivity & Table Verification")
        Log.i(TAG, "Target Base URL: $baseUrl")
        Log.i(TAG, "API Key Configured: ${apiKey.isNotBlank()}")
        Log.i(TAG, "Target Table: public.automation_control")
        Log.i(TAG, "==================================================")

        if (apiKey.isBlank() || baseUrl.isBlank()) {
            val errMsg = "Supabase URL or API Key is missing in BuildConfig!"
            Log.e(TAG, errMsg)
            return@withContext SupabaseResult.Error(statusCode = null, message = errMsg, rawErrorBody = null)
        }

        try {
            val authHeader = "Bearer $apiKey"
            val response = apiService.getAutomationControl(
                apiKey = apiKey,
                authorization = authHeader,
                select = "*"
            )

            val statusCode = response.code()
            Log.i(TAG, "HTTP Response Code: $statusCode")

            if (response.isSuccessful) {
                val data = response.body().orEmpty()
                Log.i(TAG, "CONNECTIVITY SUCCESS (HTTP $statusCode)!")
                Log.i(TAG, "Fetched ${data.size} row(s) from 'automation_control'.")
                data.forEachIndexed { index, row ->
                    Log.i(TAG, "Row [$index] -> ID: ${row.id}, Enabled: ${row.enabled}, DailyMasterEpisodes: ${row.dailyMasterEpisodes}, LastHeartbeat: ${row.lastHeartbeat}")
                }
                return@withContext SupabaseResult.Success(
                    statusCode = statusCode,
                    items = data,
                    rawJson = data.toString()
                )
            } else {
                val errorBodyStr = response.errorBody()?.string().orEmpty()
                Log.w(TAG, "HTTP Error Status: $statusCode | Body: $errorBodyStr")

                // Specifically detect and parse PostgREST table not found (PGRST205) / 404 error
                if (statusCode == 404 || errorBodyStr.contains("PGRST205") || errorBodyStr.contains("Could not find the table")) {
                    Log.e(TAG, ">>> SPECIFIC ERROR CAUGHT: PGRST205 / 404 (Table 'public.automation_control' does not exist in schema cache!)")
                    Log.e(TAG, "Action required: Execute 'backend/database/supabase_migration.sql' in Supabase SQL Editor.")
                    return@withContext SupabaseResult.TableNotFound(
                        statusCode = statusCode,
                        errorCode = "PGRST205",
                        message = "Table 'public.automation_control' not found in schema cache. Migration required."
                    )
                }

                return@withContext SupabaseResult.Error(
                    statusCode = statusCode,
                    message = "Supabase request returned HTTP $statusCode",
                    rawErrorBody = errorBodyStr
                )
            }
        } catch (e: Exception) {
            Log.e(TAG, "Network or parsing exception during Supabase GET: ${e.message}", e)
            return@withContext SupabaseResult.Error(
                statusCode = null,
                message = "Exception: ${e.javaClass.simpleName}: ${e.message}",
                rawErrorBody = null
            )
        }
    }
}
