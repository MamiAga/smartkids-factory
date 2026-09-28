package com.example.data.repository

import com.example.data.api.GeminiClient
import com.example.data.api.GeminiResponse
import com.example.data.local.*
import androidx.room.withTransaction
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.withContext
import java.security.MessageDigest

/** The 10 factory languages (backend/engine/languages.py). Order = display order in the app. */
val FACTORY_LANGUAGES = listOf(
    "EN" to "English", "ES" to "Español", "PT" to "Português", "FR" to "Français", "DE" to "Deutsch",
    "IT" to "Italiano", "TR" to "Türkçe", "RU" to "Русский", "AR" to "العربية", "HI" to "हिन्दी"
)
val FACTORY_LANGUAGE_CODES = FACTORY_LANGUAGES.map { it.first }.toSet()
val DISTRIBUTION_MODES = listOf("MULTI_CHANNEL", "SINGLE_CHANNEL", "SINGLE_CHANNEL_MULTI_AUDIO")

class SmartKidsRepository(
    private val database: SmartKidsDatabase,
    private val geminiClient: GeminiClient = GeminiClient()
) {
    val allVoices: Flow<List<VoiceLicenseEntity>> = database.voiceDao().getAllVoices()
    val allEpisodes: Flow<List<EpisodeDnaEntity>> = database.episodeDao().getAllEpisodes()
    val allJobs: Flow<List<PipelineJobEntity>> = database.pipelineDao().getAllJobs()
    val allChatMessages: Flow<List<ChatMessageEntity>> = database.chatDao().getAllMessages()
    val unapprovedOrBlockedCount: Flow<Int> = database.voiceDao().getUnapprovedOrBlockedCount()
    val automationControl: Flow<AutomationControlEntity?> = database.automationControlDao().getControl()
    val systemEvents: Flow<List<SystemEventEntity>> = database.systemEventDao().getRecentEvents()

    suspend fun initializeDatabaseDefaults() = withContext(Dispatchers.IO) {
        val existingVoices = database.voiceDao().getAllVoices().firstOrNull()
        if (existingVoices.isNullOrEmpty()) {
            // Every language is narrated by Chatterbox (MIT); the narrator timbre is a reference clip the
            // factory generates itself with Kokoro-82M (Apache-2.0). No non-commercial model is used.
            val initialVoices = FACTORY_LANGUAGES.map { (code, name) ->
                VoiceLicenseEntity(
                    voiceId = "chatterbox_${code.lowercase()}",
                    languageCode = code,
                    languageName = name,
                    modelName = if (code == "EN") "Chatterbox (English)" else "Chatterbox Multilingual v2",
                    modelPath = "huggingface:ResembleAI/chatterbox",
                    modelHashSha256 = "pip chatterbox-tts==0.1.7",
                    engineLicense = "MIT",
                    modelLicense = "MIT",
                    datasetLicense = "Resemble AI model card (MIT)",
                    isCommercialUseAllowed = true,
                    isAttributionRequired = true,
                    attributionText = "Voice: Chatterbox TTS (MIT License); reference voice Kokoro-82M (Apache License 2.0)",
                    sourceUrl = "https://github.com/resemble-ai/chatterbox",
                    modelCardUrl = "https://huggingface.co/ResembleAI/chatterbox",
                    isApproved = true,
                    auditNotes = "MIT model + in-house Apache-2.0 synthetic reference voice: commercial use permitted. " +
                        "Every take passes the voice guard (Whisper transcript + timbre drift + robotic-pitch check)."
                )
            }
            database.voiceDao().insertVoices(initialVoices)
        }

        val existingEpisodes = database.episodeDao().getAllEpisodes().firstOrNull()
        if (existingEpisodes.isNullOrEmpty()) {
            val initialEpisodes = listOf(
                EpisodeDnaEntity(
                    episodeId = "EP-SAFARI-001",
                    version = "2.0.0",
                    title = "Color Safari: Five Friendly Animals",
                    ageGroup = "2-4",
                    formatType = "Concept Exploration",
                    learningObjective = "Identify 5 primary colors (Red, Blue, Yellow, Green, Orange) paired with animal sounds",
                    difficulty = "Beginner",
                    targetDurationSeconds = 120,
                    minDurationSeconds = 110,
                    maxDurationSeconds = 130,
                    charactersJson = """[{"id":"milo_monkey","name":"Milo the Monkey","role":"Guide"},{"id":"leo_lion","name":"Leo the Lion","role":"Friend"}]""",
                    visualStyle = "Pastel Flat Vector with rounded safety edges, 60 FPS FFmpeg render",
                    musicProfile = "Uplifting marimba + playful acoustic ukulele, 105 BPM, C-Major",
                    scenesJson = """[{"scene_number":1,"name":"Intro Greeting","speech":"Welcome to the Color Safari! Let us find 5 bright colors!","visual_items":1,"target_color":"Sky Blue"},{"scene_number":2,"name":"Red Apple Tree","speech":"Look! 1 Red Apple on the branch!","visual_items":1,"target_color":"Red"},{"scene_number":3,"name":"Yellow Sun","speech":"Look up! 1 Warm Yellow Sun!","visual_items":1,"target_color":"Yellow"},{"scene_number":4,"name":"Green Leaf Frog","speech":"Ribbit! 1 Green Frog on a lily pad!","visual_items":1,"target_color":"Green"},{"scene_number":5,"name":"Orange Butterfly","speech":"Flutter flutter! 1 Orange Butterfly!","visual_items":1,"target_color":"Orange"}]""",
                    safetyProfile = "Zero flashing lights, no fast zoom, capped at 120 cd/m2, soothing tone",
                    qaStatus = "PASSED_QA"
                ),
                EpisodeDnaEntity(
                    episodeId = "EP-COUNT-002",
                    version = "2.0.0",
                    title = "Count the Stars in Rocket Flight",
                    ageGroup = "4-6",
                    formatType = "Counting",
                    learningObjective = "Count sequentially from 1 to 5 with visual pointer and audio reinforcement",
                    difficulty = "Beginner",
                    targetDurationSeconds = 150,
                    minDurationSeconds = 140,
                    maxDurationSeconds = 160,
                    charactersJson = """[{"id":"pip_star","name":"Pip the Star Traveler","role":"Narrator"}]""",
                    visualStyle = "Deep indigo cosmic canvas with gentle pastel floating geometric stars",
                    musicProfile = "Ambient celesta & soft chime synthesizer, 90 BPM",
                    scenesJson = """[{"scene_number":1,"name":"Launch Pad","speech":"Ready for blastoff? Let's count 5 shining stars!","visual_items":0},{"scene_number":2,"name":"Star One","speech":"One sparkling star!","visual_items":1},{"scene_number":3,"name":"Star Two","speech":"Two glowing stars!","visual_items":2},{"scene_number":4,"name":"Star Three","speech":"Three magical stars!","visual_items":3},{"scene_number":5,"name":"Star Four","speech":"Four bright stars!","visual_items":4},{"scene_number":6,"name":"Star Five","speech":"Five cosmic stars! We did it!","visual_items":5}]""",
                    safetyProfile = "Gentle velocity, rhythmic pauses between speech segments (2.2s interaction pause)",
                    qaStatus = "PASSED_QA"
                )
            )
            for (ep in initialEpisodes) {
                database.episodeDao().insertEpisode(ep)
            }
        }

        // No demo/sample jobs: fake "yt_demo_*" rows used to inflate the produced-video counter.
        // Real jobs come only from Supabase pipeline_jobs (see syncFromSupabaseCloud).
        listOf("JOB-EN-SAFARI-001", "JOB-DE-SAFARI-001", "JOB-TR-SAFARI-001").forEach {
            database.pipelineDao().deleteJob(it)
        }

        val existingCtrl = database.automationControlDao().getControlSnapshot()
        if (existingCtrl == null) {
            database.automationControlDao().insertOrUpdate(
                AutomationControlEntity(
                    id = 1,
                    enabled = false,
                    dailyMasterEpisodes = 1,
                    scheduleTime = "04:00",
                    timezone = "Europe/Istanbul",
                    activeLanguagesJson = "[\"EN\"]",
                    activeChannelsJson = "[\"EN\"]",
                    generationMode = "AUTONOMOUS",
                    publishMode = "AUTO",
                    distributionMode = "SINGLE_CHANNEL_MULTI_AUDIO",
                    narratorMode = "alternate",
                    ttsShards = 8
                )
            )
        }
    }

    fun calculateDeterministicSeed(episodeId: String, lang: String, version: String): String {
        val input = "$episodeId:$lang:$version"
        val bytes = MessageDigest.getInstance("SHA-256").digest(input.toByteArray())
        return bytes.joinToString("") { "%02x".format(it) }
    }

    suspend fun setVoiceApproval(voiceId: String, approved: Boolean) {
        val voice = database.voiceDao().getAllVoices().firstOrNull()?.find { it.voiceId == voiceId }
        if (voice != null) {
            // Strict gating invariant: never allow approval if commercial use is false or unknown
            if (approved && !voice.isCommercialUseAllowed) {
                throw IllegalStateException("PRODUCTION GATE VIOLATION: Cannot approve voice ${voice.voiceId} because commercial_use is not true (${voice.modelLicense})")
            }
            database.voiceDao().setApproval(voiceId, approved)
        }
    }

    suspend fun updateVoice(voice: VoiceLicenseEntity) {
        database.voiceDao().updateVoice(voice)
    }

    suspend fun saveEpisode(episode: EpisodeDnaEntity) {
        database.episodeDao().insertEpisode(episode)
    }

    suspend fun deleteEpisode(episode: EpisodeDnaEntity) {
        database.episodeDao().deleteEpisode(episode)
    }

    suspend fun saveJob(job: PipelineJobEntity) {
        database.pipelineDao().insertJob(job)
    }

    suspend fun updateJob(job: PipelineJobEntity) {
        database.pipelineDao().updateJob(job)
    }

    suspend fun sendChatMessage(
        userMessage: String,
        model: String = GeminiClient.MODEL_FLASH
    ): GeminiResponse = withContext(Dispatchers.IO) {
        val actualModel = if (model == GeminiClient.MODEL_FLASH_LITE) GeminiClient.MODEL_FLASH_LITE else GeminiClient.MODEL_FLASH

        // Save user message to database
        val userEntity = ChatMessageEntity(
            role = "user",
            content = userMessage,
            modelUsed = actualModel,
            isThinkingHigh = false,
            isSearchGrounded = false
        )
        database.chatDao().insertMessage(userEntity)

        // Fetch recent conversation history
        val historyEntities = database.chatDao().getAllMessages().firstOrNull() ?: emptyList()
        val historyList = historyEntities.takeLast(10).dropLast(1).map {
            Pair(it.role, it.content)
        }

        // Call Gemini
        val response = geminiClient.generateContent(
            prompt = userMessage,
            model = actualModel,
            conversationHistory = historyList
        )

        // Save model response
        val modelEntity = ChatMessageEntity(
            role = "model",
            content = response.text,
            modelUsed = response.modelUsed,
            isThinkingHigh = false,
            isSearchGrounded = false
        )
        database.chatDao().insertMessage(modelEntity)

        response
    }

    suspend fun clearChatHistory() {
        database.chatDao().clearHistory()
    }

    suspend fun performEducationalQa(episode: EpisodeDnaEntity): GeminiResponse {
        val prompt = """
            Perform strict Educational QA on this Episode DNA:
            Title: ${episode.title}
            Age Group: ${episode.ageGroup}
            Format: ${episode.formatType}
            Objective: ${episode.learningObjective}
            Scenes Data: ${episode.scenesJson}
            
            Verify the 3 Core Gating Invariants:
            1. Auditory vs. Visual Invariant: If speech says "N items / colors", are exactly N items displayed in scenes?
            2. Age Appropriateness: Are words, syllable complexity, and pause durations suitable for ${episode.ageGroup}?
            3. Engagement & Safety: No strobe effects, clear positive reinforcement.
            
            Return a verdict: [PASSED] or [FAILED - Reason].
        """.trimIndent()

        return geminiClient.generateContent(
            prompt = prompt,
            model = GeminiClient.MODEL_FLASH
        )
    }

    suspend fun generateLocalizedScript(episode: EpisodeDnaEntity, targetLang: String): GeminiResponse {
        val prompt = """
            Generate an authentic, culturally natural educational localization of Episode DNA:
            Source Title: ${episode.title}
            Target Language: $targetLang (One of: EN, ES, DE, FR, PT, AR, HI, ZH, JA, TR)
            Age Group: ${episode.ageGroup}
            Learning Objective: ${episode.learningObjective}
            Scenes: ${episode.scenesJson}
            
            Rules:
            1. Preserve master educational objective exactly.
            2. Localize dialogue, animal sounds, number phrasing, and interactive cues.
            3. Maintain timing and 2.0s interaction pauses.
            Format output cleanly as localized JSON scenes.
        """.trimIndent()

        return geminiClient.generateContent(
            prompt = prompt,
            model = GeminiClient.MODEL_FLASH_LITE
        )
    }

    /**
     * Statically inspects the full license and model card chain.
     */
    fun verifyVoiceStaticAudit(voice: VoiceLicenseEntity): String {
        return buildString {
            append("STATIC REGISTRY AUDIT RECORD:\n")
            append("• Language: ${voice.languageName} [${voice.languageCode}]\n")
            append("• Model Name: ${voice.modelName}\n")
            append("• Model Path: ${voice.modelPath}\n")
            append("• Engine License: ${voice.engineLicense}\n")
            append("• Model License: ${voice.modelLicense}\n")
            append("• Dataset License: ${voice.datasetLicense}\n")
            append("• Commercial Monetization: ${if (voice.isCommercialUseAllowed) "✅ EXPLICITLY PERMITTED" else "❌ NOT PERMITTED (BLOCKER)"}\n")
            append("• Attribution Required: ${if (voice.isAttributionRequired) "Yes (${voice.attributionText})" else "No"}\n")
            append("• Model Card URL: ${voice.modelCardUrl}\n")
            append("• Upstream Source: ${voice.sourceUrl}\n")
            append("• SHA-256 Checksum: ${voice.modelHashSha256}\n")
            append("• Gating Status: ${if (voice.isApproved) "APPROVED FOR PRODUCTION" else "HARD BLOCKED"}\n")
            append("• Audit Finding: ${voice.auditNotes}")
        }
    }

    /**
     * START/STOP. Returns true only if Supabase (source of truth) accepted the change.
     * The local switch is updated only after the cloud write succeeds, so the UI can never
     * show "ÜRETİM AÇIK" while the cloud factory is actually still disabled.
     */
    suspend fun toggleAutomationControl(enabled: Boolean): Boolean = withContext(Dispatchers.IO) {
        val ctrl = database.automationControlDao().getControlSnapshot()
        val ok = syncControlToSupabase(
            enabled,
            ctrl?.dailyMasterEpisodes ?: 1,
            ctrl?.activeLanguagesJson ?: "[\"EN\"]"
        )
        if (ok) {
            database.automationControlDao().setEnabled(enabled)
            val eventType = if (enabled) "FACTORY_ENABLED" else "FACTORY_DISABLED"
            val msg = if (enabled) "Kullanıcı bulut üretim fabrikasını [BAŞLATTI] (Supabase enabled=true)." else "Kullanıcı bulut üretim fabrikasını [DURDURDU] (Supabase enabled=false)."
            recordSystemEvent(eventType, msg, if (enabled) "INFO" else "WARNING")
        } else {
            recordSystemEvent("CLOUD_WRITE_FAILED", "Supabase automation_control güncellenemedi (enabled=$enabled).", "ERROR")
        }
        ok
    }

    suspend fun updateDailyMasterEpisodes(episodes: Int) = withContext(Dispatchers.IO) {
        val count = episodes.coerceIn(1, 10)
        database.automationControlDao().setDailyTarget(count)
        val ctrl = database.automationControlDao().getControlSnapshot()
        recordSystemEvent("TARGET_UPDATED", "Günlük master bölüm hedefi güncellendi: $count bölüm/gün")
        if (ctrl != null) {
            syncControlToSupabase(ctrl.enabled, count, ctrl.activeLanguagesJson)
        }
    }

    suspend fun updateSchedule(time: String, timezone: String) = withContext(Dispatchers.IO) {
        database.automationControlDao().setSchedule(time, timezone)
        // Previously only stored locally, so the cloud factory never saw the new time.
        val ok = patchControlRemote("""{"schedule_time":"$time","timezone":"$timezone"}""")
        recordSystemEvent(
            "SCHEDULE_UPDATED",
            if (ok) "Üretim saati güncellendi: $time ($timezone)" else "Üretim saati yalnızca yerelde kaydedildi, Supabase'e yazılamadı!",
            if (ok) "INFO" else "ERROR"
        )
    }

    suspend fun toggleActiveLanguage(langCode: String) = withContext(Dispatchers.IO) {
        if (langCode !in FACTORY_LANGUAGE_CODES) return@withContext
        val ctrl = database.automationControlDao().getControlSnapshot() ?: return@withContext
        val currentLangs = try {
            val list = mutableListOf<String>()
            val cleaned = ctrl.activeLanguagesJson.trim().removeSurrounding("[", "]")
            if (cleaned.isNotBlank()) {
                cleaned.split(",").map { it.trim().removeSurrounding("\"") }.filter { it.isNotEmpty() }.forEach { list.add(it) }
            }
            list
        } catch (e: Exception) {
            mutableListOf("EN")
        }

        if (currentLangs.contains(langCode)) {
            if (currentLangs.size > 1) { // Keep at least one language
                currentLangs.remove(langCode)
            }
        } else {
            currentLangs.add(langCode)
        }

        val json = "[" + currentLangs.joinToString(",") { "\"$it\"" } + "]"
        database.automationControlDao().setActiveLanguages(json)
        recordSystemEvent("LANGUAGES_UPDATED", "Aktif diller güncellendi: $json")
        syncControlToSupabase(ctrl.enabled, ctrl.dailyMasterEpisodes, json)
        Unit
    }

    suspend fun recordSystemEvent(eventType: String, message: String, severity: String = "INFO") = withContext(Dispatchers.IO) {
        database.systemEventDao().insertEvent(
            SystemEventEntity(
                eventType = eventType,
                severity = severity,
                message = message
            )
        )
    }

    suspend fun syncFromSupabaseCloud(): String = withContext(Dispatchers.IO) {
        try {
            val supabaseUrl = com.example.BuildConfig.SUPABASE_URL.trimEnd('/')
            val anonKey = com.example.BuildConfig.SUPABASE_ANON_KEY
            if (supabaseUrl.isBlank() || anonKey.isBlank() || supabaseUrl.contains("DEFAULT_")) {
                return@withContext "Supabase bağlantı bilgileri eksik."
            }

            // 1. Fetch automation_control
            val url = java.net.URL("$supabaseUrl/rest/v1/automation_control?id=eq.1&select=*")
            val conn = url.openConnection() as java.net.HttpURLConnection
            conn.requestMethod = "GET"
            conn.setRequestProperty("apikey", anonKey)
            conn.setRequestProperty("Authorization", "Bearer $anonKey")
            conn.setRequestProperty("Accept", "application/json")
            conn.connectTimeout = 5000
            conn.readTimeout = 5000

            val code = conn.responseCode
            if (code == 200) {
                val responseText = conn.inputStream.bufferedReader().use { it.readText() }
                val jsonArray = org.json.JSONArray(responseText)
                if (jsonArray.length() > 0) {
                    val obj = jsonArray.getJSONObject(0)
                    val enabled = obj.optBoolean("enabled", false)
                    val daily = obj.optInt("daily_master_episodes", 1)
                    val scheduleTime = obj.optString("schedule_time", "04:00")
                    val timezone = obj.optString("timezone", "Europe/Istanbul")
                    val langs = obj.opt("active_languages")?.toString() ?: "[\"EN\"]"
                    val channels = obj.opt("active_channels")?.toString() ?: "[\"EN\"]"
                    val failureCount = obj.optInt("failure_count", 0)
                    val currentJobId = if (obj.isNull("current_job_id")) null else obj.optString("current_job_id")
                    val heartbeatStr = if (obj.isNull("last_heartbeat")) null else obj.optString("last_heartbeat")
                    val cloudHeartbeat = parseIsoTimestamp(heartbeatStr)
                    // columns added by backend/database/2026-09-28_multilanguage.sql (defaults if not migrated yet)
                    val distributionMode = obj.optString("distribution_mode", "SINGLE_CHANNEL_MULTI_AUDIO").ifBlank { "SINGLE_CHANNEL_MULTI_AUDIO" }
                    val narratorMode = obj.optString("narrator_mode", "alternate").ifBlank { "alternate" }
                    val ttsShards = obj.optInt("tts_shards", 8)
                    val nextRun = parseIsoTimestamp(if (obj.isNull("next_run_at")) null else obj.optString("next_run_at"))
                    val lastRun = parseIsoTimestamp(if (obj.isNull("last_run_at")) null else obj.optString("last_run_at"))
                    migrationApplied = obj.has("distribution_mode")

                    val existing = database.automationControlDao().getControlSnapshot()
                    val updated = (existing ?: AutomationControlEntity(id = 1)).copy(
                        enabled = enabled,
                        dailyMasterEpisodes = daily,
                        scheduleTime = scheduleTime,
                        timezone = timezone,
                        activeLanguagesJson = langs,
                        activeChannelsJson = channels,
                        failureCount = failureCount,
                        currentJobId = currentJobId,
                        lastHeartbeat = cloudHeartbeat,
                        distributionMode = distributionMode,
                        narratorMode = narratorMode,
                        ttsShards = ttsShards,
                        nextRunAt = if (nextRun > 0L) nextRun else null,
                        lastRunAt = if (lastRun > 0L) lastRun else null
                    )
                    database.automationControlDao().insertOrUpdate(updated)
                    recordSystemEvent("CLOUD_SYNC", "Supabase automation_control başarıyla senkronize edildi (enabled=$enabled, hedef=$daily)")
                }
                conn.disconnect()
            } else {
                conn.disconnect()
                return@withContext "Supabase HTTP $code yanıtı verdi."
            }

            // 2. Fetch recent pipeline_jobs (10 languages -> more rows)
            try {
                val jobsUrl = java.net.URL("$supabaseUrl/rest/v1/pipeline_jobs?select=*&order=updated_at.desc&limit=60")
                val jobsConn = jobsUrl.openConnection() as java.net.HttpURLConnection
                jobsConn.requestMethod = "GET"
                jobsConn.setRequestProperty("apikey", anonKey)
                jobsConn.setRequestProperty("Authorization", "Bearer $anonKey")
                jobsConn.setRequestProperty("Accept", "application/json")
                jobsConn.connectTimeout = 5000
                jobsConn.readTimeout = 5000

                if (jobsConn.responseCode == 200) {
                    val jobsText = jobsConn.inputStream.bufferedReader().use { it.readText() }
                    val jobsArr = org.json.JSONArray(jobsText)
                    val cloudJobs = mutableListOf<PipelineJobEntity>()
                    for (i in 0 until jobsArr.length()) {
                        val j = jobsArr.getJSONObject(i)
                        val jId = j.optString("job_id", "")
                        if (jId.isBlank()) continue
                        val epId = j.optString("episode_id", "")
                        val lang = j.optString("language", "EN")
                        val state = j.optString("state", "CREATED")
                        val ytId = if (j.isNull("youtube_video_id")) "" else j.optString("youtube_video_id", "")
                        val err = if (j.isNull("error_message")) "" else j.optString("error_message", "")
                        val proc = if (j.isNull("processing_status")) "" else j.optString("processing_status", "")
                        val updated = parseIsoTimestamp(if (j.isNull("updated_at")) null else j.optString("updated_at"))
                        val narrator = if (j.isNull("narrator")) "" else j.optString("narrator", "")
                        val detail = if (j.isNull("stage_detail")) "" else j.optString("stage_detail", "")
                        val pct = if (j.isNull("progress_pct")) 0 else j.optInt("progress_pct", 0)
                        cloudJobs.add(
                            PipelineJobEntity(
                                jobId = jId,
                                episodeId = epId,
                                title = "SmartKids Bölüm: $epId ($lang${if (narrator.isNotBlank()) ", " + (if (narrator == "male") "erkek" else "kız") + " anlatıcı" else ""})",
                                languageCode = lang,
                                status = state,
                                deterministicSeed = if (j.isNull("deterministic_seed")) "" else j.optString("deterministic_seed", ""),
                                renderDurationSeconds = j.optDouble("render_duration_sec", 0.0).let { if (it.isNaN()) 0.0 else it },
                                youtubeVideoId = ytId,
                                costUsd = j.optDouble("cost_usd", 0.0).let { if (it.isNaN()) 0.0 else it },
                                technicalQaPassed = j.optBoolean("technical_qa_passed", false),
                                educationalQaPassed = j.optBoolean("educational_qa_passed", false),
                                logMessage = buildString {
                                    append("Bulut durumu: $state")
                                    if (proc.isNotBlank()) append(" | YouTube işleme: $proc")
                                    if (ytId.isNotBlank()) append(" | https://youtu.be/$ytId")
                                    if (detail.isNotBlank()) append(" | $detail")
                                    if (err.isNotBlank()) append(" | HATA: $err")
                                },
                                narrator = narrator,
                                progressPct = pct,
                                stageDetail = detail,
                                updatedAt = if (updated > 0L) updated else System.currentTimeMillis()
                            )
                        )
                    }
                    // Replace, don't merge: removes stale local-only/fake rows that never existed in the cloud.
                    database.withTransaction {
                        database.pipelineDao().deleteAllJobs()
                        database.pipelineDao().insertJobs(cloudJobs)
                    }
                }
                jobsConn.disconnect()
            } catch (e: Exception) {
                // Table might not exist yet or empty, proceed
            }

            return@withContext "Supabase bulut verileri başarıyla senkronize edildi!"
        } catch (e: Exception) {
            return@withContext "Senkronizasyon hatası: ${e.message}"
        }
    }

    /**
     * Manual test run (production_pipeline.yml): one episode in the chosen languages, same parallel pipeline
     * as the autonomous factory. Idempotent on the cloud side (a language that already has a video is skipped).
     */
    suspend fun triggerGitHubWorkflowDispatch(
        episodeId: String,
        languages: List<String>,
        mode: String = "SINGLE_CHANNEL_MULTI_AUDIO",
        narrator: String = "alternate",
        dryRun: Boolean = false
    ): Result<String> {
        val langs = languages.filter { it in FACTORY_LANGUAGE_CODES }.ifEmpty { listOf("EN") }.joinToString(" ")
        return dispatchWorkflow(
            "production_pipeline.yml",
            """{"ref":"main","inputs":{"episode_id":"$episodeId","languages":"$langs","mode":"$mode","narrator":"$narrator","dry_run":"$dryRun"}}"""
        )
    }

    /** Local flag: false when the Supabase table still lacks the 2026-09-28 columns. */
    @Volatile var migrationApplied: Boolean = true
        private set

    suspend fun updateDistributionMode(mode: String): Boolean = withContext(Dispatchers.IO) {
        if (mode !in DISTRIBUTION_MODES) return@withContext false
        val ok = patchControlRemote("""{"distribution_mode":"$mode"}""")
        if (ok) database.automationControlDao().setDistributionMode(mode)
        recordSystemEvent("DISTRIBUTION_UPDATED", if (ok) "Yayın modeli: $mode" else "Yayın modeli yazılamadı (Supabase SQL güncellemesi gerekli olabilir)", if (ok) "INFO" else "ERROR")
        ok
    }

    suspend fun updateNarratorMode(mode: String): Boolean = withContext(Dispatchers.IO) {
        if (mode !in listOf("alternate", "female", "male")) return@withContext false
        val ok = patchControlRemote("""{"narrator_mode":"$mode"}""")
        if (ok) database.automationControlDao().setNarratorMode(mode)
        recordSystemEvent("NARRATOR_UPDATED", if (ok) "Anlatıcı: $mode" else "Anlatıcı ayarı yazılamadı", if (ok) "INFO" else "ERROR")
        ok
    }

    suspend fun updateTtsShards(shards: Int): Boolean = withContext(Dispatchers.IO) {
        val n = shards.coerceIn(1, 20)
        val ok = patchControlRemote("""{"tts_shards":$n}""")
        if (ok) database.automationControlDao().setTtsShards(n)
        recordSystemEvent("SHARDS_UPDATED", if (ok) "Paralel seslendirme sunucusu: $n / dil" else "Paralel sunucu sayısı yazılamadı", if (ok) "INFO" else "ERROR")
        ok
    }

    /**
     * STOP -> also cancel factory runs that are already running on GitHub (narration runners included),
     * so nothing keeps working in the background. Needs the PAT with "Actions: Read and write".
     * Safe: every job is idempotent and the narration cache survives a cancel.
     */
    suspend fun cancelRunningFactoryRuns(): Result<Int> = withContext(Dispatchers.IO) {
        try {
            val pat = com.example.BuildConfig.GITHUB_PAT
            if (pat.isBlank() || pat == "DEFAULT_GITHUB_PAT") return@withContext Result.failure(Exception("GitHub PAT yok"))
            var cancelled = 0
            for (wf in listOf("smartkids_factory.yml", "production_pipeline.yml")) {
                for (status in listOf("in_progress", "queued")) {
                    val list = githubRequest("GET", "actions/workflows/$wf/runs?status=$status&per_page=20", null)
                    val runs = org.json.JSONObject(list).optJSONArray("workflow_runs") ?: continue
                    for (i in 0 until runs.length()) {
                        val id = runs.getJSONObject(i).optLong("id")
                        if (id > 0) {
                            githubRequest("POST", "actions/runs/$id/cancel", "")
                            cancelled++
                        }
                    }
                }
            }
            if (cancelled > 0) recordSystemEvent("GITHUB_RUNS_CANCELLED", "$cancelled bulut çalışması durduruldu (STOP)", "WARNING")
            Result.success(cancelled)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private fun githubRequest(method: String, path: String, body: String?): String {
        val pat = com.example.BuildConfig.GITHUB_PAT
        val conn = java.net.URL("https://api.github.com/repos/MamiAga/smartkids-factory/$path").openConnection() as java.net.HttpURLConnection
        conn.requestMethod = method
        conn.setRequestProperty("Authorization", "Bearer $pat")
        conn.setRequestProperty("Accept", "application/vnd.github+json")
        conn.setRequestProperty("X-GitHub-Api-Version", "2022-11-28")
        conn.setRequestProperty("User-Agent", "SmartKids-Android-Cockpit")
        conn.connectTimeout = 8000
        conn.readTimeout = 8000
        if (body != null) {
            conn.doOutput = true
            conn.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
        }
        val code = conn.responseCode
        val text = (if (code in 200..299) conn.inputStream else conn.errorStream)?.bufferedReader()?.use { it.readText() } ?: ""
        conn.disconnect()
        if (code !in 200..299) throw Exception("GitHub API $code: ${text.take(160)}")
        return text
    }

    private fun parseIsoTimestamp(isoString: String?): Long {
        if (isoString.isNullOrBlank() || isoString == "null") return 0L
        return try {
            java.time.Instant.parse(isoString).toEpochMilli()
        } catch (e: Exception) {
            try {
                val sdf = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", java.util.Locale.US).apply {
                    timeZone = java.util.TimeZone.getTimeZone("UTC")
                }
                sdf.parse(isoString.substring(0, 19))?.time ?: 0L
            } catch (e2: Exception) {
                0L
            }
        }
    }

    private suspend fun syncControlToSupabase(enabled: Boolean, dailyEpisodes: Int, languagesJson: String): Boolean =
        patchControlRemote("""{"enabled":$enabled,"daily_master_episodes":$dailyEpisodes,"active_languages":$languagesJson}""")

    /** PATCH automation_control id=1. Returns true only on HTTP 2xx (errors are no longer swallowed). */
    private suspend fun patchControlRemote(jsonPayload: String): Boolean = withContext(Dispatchers.IO) {
        try {
            val supabaseUrl = com.example.BuildConfig.SUPABASE_URL.trimEnd('/')
            val anonKey = com.example.BuildConfig.SUPABASE_ANON_KEY
            if (supabaseUrl.isEmpty() || anonKey.isEmpty() || supabaseUrl.contains("DEFAULT_")) return@withContext false
            val url = java.net.URL("$supabaseUrl/rest/v1/automation_control?id=eq.1")
            val conn = url.openConnection() as java.net.HttpURLConnection
            conn.requestMethod = "PATCH"
            conn.setRequestProperty("apikey", anonKey)
            conn.setRequestProperty("Authorization", "Bearer $anonKey")
            conn.setRequestProperty("Content-Type", "application/json")
            // return=representation: an RLS-blocked PATCH returns 200 with [] -> we detect it as failure
            conn.setRequestProperty("Prefer", "return=representation")
            conn.connectTimeout = 8000
            conn.readTimeout = 8000
            conn.doOutput = true
            conn.outputStream.use { it.write(jsonPayload.toByteArray(Charsets.UTF_8)) }
            val code = conn.responseCode
            val body = if (code in 200..299) conn.inputStream.bufferedReader().use { it.readText() } else ""
            conn.disconnect()
            code in 200..299 && body.trim().let { it.startsWith("[") && it != "[]" }
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Android START -> run the ONE production entry point (smartkids_factory.yml) immediately.
     * The workflow itself re-checks enabled / daily target / idempotency, so pressing START
     * twice can never produce a duplicate video.
     */
    suspend fun triggerFactoryRunNow(): Result<String> =
        dispatchWorkflow("smartkids_factory.yml", """{"ref":"main","inputs":{"run_now":"true"}}""")

    private suspend fun dispatchWorkflow(workflowFile: String, body: String): Result<String> = withContext(Dispatchers.IO) {
        try {
            val pat = com.example.BuildConfig.GITHUB_PAT
            if (pat.isBlank() || pat == "DEFAULT_GITHUB_PAT") {
                return@withContext Result.failure(Exception("GitHub PAT yapılandırılmamış (.env GITHUB_PAT). Fabrika yine de saatlik zamanlayıcıyla çalışır."))
            }
            val url = java.net.URL("https://api.github.com/repos/MamiAga/smartkids-factory/actions/workflows/$workflowFile/dispatches")
            val conn = url.openConnection() as java.net.HttpURLConnection
            conn.requestMethod = "POST"
            conn.setRequestProperty("Authorization", "Bearer $pat")
            conn.setRequestProperty("Accept", "application/vnd.github+json")
            conn.setRequestProperty("X-GitHub-Api-Version", "2022-11-28")
            conn.setRequestProperty("User-Agent", "SmartKids-Android-Cockpit")
            conn.setRequestProperty("Content-Type", "application/json")
            conn.connectTimeout = 8000
            conn.readTimeout = 8000
            conn.doOutput = true
            conn.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            val code = conn.responseCode
            if (code in 200..204) {
                conn.disconnect()
                recordSystemEvent("GITHUB_DISPATCH", "GitHub Actions $workflowFile tetiklendi (HTTP $code)")
                Result.success("GitHub Actions $workflowFile başlatıldı (HTTP $code)")
            } else {
                val err = conn.errorStream?.bufferedReader()?.use { it.readText() } ?: "HTTP $code"
                conn.disconnect()
                Result.failure(Exception("GitHub API $code: ${err.take(200)}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}

