package com.example.data.api

import android.util.Log
import com.example.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit
import kotlin.random.Random

data class GeminiResponse(
    val text: String,
    val isSuccess: Boolean,
    val modelUsed: String,
    val errorMessage: String? = null
)

/**
 * GeminiClient refactored for maximum resilience:
 * - Primary models: gemini-3.6-flash, gemini-3.1-flash-lite-preview
 * - Fallback models: gemini-3.5-flash, gemini-flash-latest
 * - Robust handling for HTTP 503 (High demand / UNAVAILABLE), HTTP 429 (Rate Limit), and HTTP 404 (Deprecated / Not found)
 * - Automatic exponential backoff + jitter and transparent fallback model failover
 */
class GeminiClient {
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    companion object {
        const val MODEL_FLASH_3_6 = "gemini-3.6-flash"
        const val MODEL_FLASH_3_5 = "gemini-3.5-flash"
        const val MODEL_FLASH_LITE = "gemini-3.1-flash-lite-preview"
        const val MODEL_FLASH_LATEST = "gemini-flash-latest"

        // Primary default model recommended by Google Gemini API
        const val MODEL_FLASH = MODEL_FLASH_3_6

        const val DEFAULT_SYSTEM_INSTRUCTION =
            "You are the Chief Master Architect & Curriculum Lead for the SmartKids Autonomous Learning Network. " +
            "You enforce the locked master architecture: 0 TL cost guard, Oracle OCI Always Free ARM (2 OCPU, 12GB RAM), " +
            "Piper TTS commercial-safe licensing (XTTS-v2 strictly banned due to CPML), 10-language matrix (EN, ES, DE, FR, PT, AR, HI, ZH, JA, TR), " +
            "strict Episode DNA schemas, Educational QA gates (verifying auditory numbers match visual items), and safe YouTube upload state machines. " +
            "Provide rigorous, precise architectural blueprints, schema DDLs, and pedagogical insights."
    }

    suspend fun generateContent(
        prompt: String,
        model: String = MODEL_FLASH,
        conversationHistory: List<Pair<String, String>> = emptyList(), // Pair(role, text)
        systemInstruction: String = DEFAULT_SYSTEM_INSTRUCTION
    ): GeminiResponse = withContext(Dispatchers.IO) {
        val apiKey = BuildConfig.GEMINI_API_KEY
        if (apiKey.isNullOrBlank()) {
            return@withContext GeminiResponse(
                text = "⚠️ Gemini API key is missing. Please configure GEMINI_API_KEY in the AI Studio Secrets panel (.env) to enable live autonomous AI operations.",
                isSuccess = false,
                modelUsed = model,
                errorMessage = "API_KEY_MISSING"
            )
        }

        // Build request payload using standard Android JSONObject
        val rootJson = JSONObject()

        // 1. System Instruction
        val sysInstructionObj = JSONObject()
        val sysPartsArray = JSONArray().put(JSONObject().put("text", systemInstruction))
        sysInstructionObj.put("parts", sysPartsArray)
        rootJson.put("systemInstruction", sysInstructionObj)

        // 2. Contents (Multi-turn conversation history + new prompt)
        val contentsArray = JSONArray()
        for ((role, text) in conversationHistory) {
            val contentObj = JSONObject()
            val mappedRole = if (role.equals("model", ignoreCase = true)) "model" else "user"
            contentObj.put("role", mappedRole)
            contentObj.put("parts", JSONArray().put(JSONObject().put("text", text)))
            contentsArray.put(contentObj)
        }
        // Current user prompt
        val currentContent = JSONObject()
        currentContent.put("role", "user")
        currentContent.put("parts", JSONArray().put(JSONObject().put("text", prompt)))
        contentsArray.put(currentContent)
        rootJson.put("contents", contentsArray)

        val requestBodyString = rootJson.toString()

        // Construct prioritized model failover chain
        val requestedModel = when (model) {
            "gemini-3.5-flash-lite", MODEL_FLASH_LITE -> MODEL_FLASH_LITE
            "gemini-3.5-flash", MODEL_FLASH_3_5 -> MODEL_FLASH_3_5
            "gemini-3.6-flash", MODEL_FLASH_3_6 -> MODEL_FLASH_3_6
            else -> MODEL_FLASH_3_6
        }

        val modelChain = mutableListOf<String>()
        modelChain.add(requestedModel)
        if (requestedModel == MODEL_FLASH_3_6) {
            modelChain.add(MODEL_FLASH_3_5)
            modelChain.add(MODEL_FLASH_LATEST)
            modelChain.add(MODEL_FLASH_LITE)
        } else if (requestedModel == MODEL_FLASH_LITE) {
            modelChain.add(MODEL_FLASH_3_6)
            modelChain.add(MODEL_FLASH_3_5)
            modelChain.add(MODEL_FLASH_LATEST)
        } else {
            modelChain.add(MODEL_FLASH_3_6)
            modelChain.add(MODEL_FLASH_LATEST)
            modelChain.add(MODEL_FLASH_LITE)
        }

        var lastErrorMsg: String? = null
        var lastHttpCode = 0

        for (candidateModel in modelChain) {
            val url = "https://generativelanguage.googleapis.com/v1beta/models/$candidateModel:generateContent?key=$apiKey"
            val requestBody = requestBodyString.toRequestBody("application/json; charset=utf-8".toMediaType())
            val request = Request.Builder()
                .url(url)
                .post(requestBody)
                .build()

            val maxAttemptsForModel = 2
            var backoffMs = 1200L

            for (attempt in 1..maxAttemptsForModel) {
                try {
                    client.newCall(request).execute().use { response ->
                        val code = response.code
                        val responseBody = response.body?.string() ?: ""
                        lastHttpCode = code

                        // Case 1: Transient overload / rate limit codes
                        if (code == 503 || code == 429 || code == 500 || code == 502 || code == 504) {
                            val jitter = Random.nextLong(200, 500)
                            val totalWait = backoffMs + jitter
                            Log.w("GeminiClient", "Model '$candidateModel' returned HTTP $code (attempt $attempt/$maxAttemptsForModel). Backing off ${totalWait}ms...")

                            if (attempt < maxAttemptsForModel) {
                                delay(totalWait)
                                backoffMs *= 2
                                return@use // retry same model
                            } else {
                                Log.w("GeminiClient", "Model '$candidateModel' exhausted attempts with HTTP $code. Trying fallback model...")
                                lastErrorMsg = if (code == 503) {
                                    "Bu model şu anda yüksek talep görüyor (HTTP 503 - UNAVAILABLE)."
                                } else if (code == 429) {
                                    "Free Tier istek sınırı aşıldı (HTTP 429)."
                                } else {
                                    "Sunucu geçici hata döndürdü (HTTP $code)."
                                }
                                return@use // continue to next candidate in modelChain
                            }
                        }

                        // Case 2: Deprecated / Not Found model (404) -> Failover immediately to next model in chain
                        if (code == 404) {
                            Log.w("GeminiClient", "Model '$candidateModel' returned HTTP 404 (NOT_FOUND / deprecated). Trying fallback model in chain...")
                            lastErrorMsg = "Model '$candidateModel' mevcut değil (HTTP 404): $responseBody"
                            return@use // continue to next candidate in modelChain without crashing
                        }

                        // Case 3: Invalid API key or permission denied (401 / 403)
                        if (code in 401..403) {
                            lastErrorMsg = "HTTP $code: $responseBody"
                            Log.e("GeminiClient", "Auth error on '$candidateModel': $lastErrorMsg")
                            return@withContext GeminiResponse(
                                text = "Gemini API Yetkilendirme Hatası (HTTP $code):\n$responseBody\nLütfen GEMINI_API_KEY değerini kontrol edin.",
                                isSuccess = false,
                                modelUsed = candidateModel,
                                errorMessage = lastErrorMsg
                            )
                        }

                        // Case 4: Other non-successful HTTP code
                        if (!response.isSuccessful) {
                            lastErrorMsg = "HTTP $code: $responseBody"
                            Log.e("GeminiClient", "Non-retryable API error on '$candidateModel': $lastErrorMsg")
                            if (code == 400) {
                                return@withContext GeminiResponse(
                                    text = "Gemini API İstek Hatası ($candidateModel - HTTP 400):\n$responseBody",
                                    isSuccess = false,
                                    modelUsed = candidateModel,
                                    errorMessage = lastErrorMsg
                                )
                            }
                            return@use // continue to fallback model
                        }

                        // Case 5: Success -> Parse candidates
                        val jsonResponse = JSONObject(responseBody)
                        val candidates = jsonResponse.optJSONArray("candidates")
                        if (candidates != null && candidates.length() > 0) {
                            val firstCandidate = candidates.getJSONObject(0)
                            val content = firstCandidate.optJSONObject("content")
                            val parts = content?.optJSONArray("parts")
                            val textBuilder = StringBuilder()
                            if (parts != null) {
                                for (i in 0 until parts.length()) {
                                    val part = parts.getJSONObject(i)
                                    if (part.has("text")) {
                                        textBuilder.append(part.getString("text"))
                                    }
                                }
                            }

                            val resultText = textBuilder.toString()
                            val finalModelLabel = if (candidateModel != requestedModel) "$candidateModel (Yedek)" else candidateModel
                            return@withContext GeminiResponse(
                                text = if (resultText.isNotBlank()) resultText else "Metin yanıtı üretilemedi.",
                                isSuccess = true,
                                modelUsed = finalModelLabel
                            )
                        } else {
                            lastErrorMsg = "Modelden aday yanıt dönmedi."
                            return@use
                        }
                    }
                } catch (e: IOException) {
                    lastErrorMsg = e.message
                    Log.e("GeminiClient", "Network exception for '$candidateModel' (attempt $attempt): ${e.message}")
                    if (attempt < maxAttemptsForModel) {
                        delay(backoffMs)
                        backoffMs *= 2
                    }
                } catch (e: Exception) {
                    Log.e("GeminiClient", "Unexpected exception for '$candidateModel': ${e.message}", e)
                    return@withContext GeminiResponse(
                        text = "Beklenmeyen hata: ${e.localizedMessage}",
                        isSuccess = false,
                        modelUsed = candidateModel,
                        errorMessage = e.message
                    )
                }
            }
        }

        // If all models in the chain were exhausted
        val userFriendlyMessage = if (lastHttpCode == 503) {
            "⚠️ Gemini servisi şu anda küresel ölçekte yüksek talep yaşıyor (HTTP 503: High Demand). İstekler yedek modeller üzerinden de denendi ancak geçici yoğunluk devam ediyor. Lütfen birkaç saniye sonra tekrar deneyin."
        } else if (lastHttpCode == 429) {
            "⏳ Gemini Free Tier kota sınırı aşıldı (HTTP 429). Lütfen kısa bir süre bekleyip tekrar deneyin."
        } else if (lastHttpCode == 404) {
            "⚠️ Belirtilen modeller kullanımdan kaldırılmış veya bulunamadı. Lütfen daha sonra tekrar deneyin."
        } else {
            "Gemini API yanıt veremedi: $lastErrorMsg"
        }

        GeminiResponse(
            text = userFriendlyMessage,
            isSuccess = false,
            modelUsed = requestedModel,
            errorMessage = lastErrorMsg
        )
    }
}
