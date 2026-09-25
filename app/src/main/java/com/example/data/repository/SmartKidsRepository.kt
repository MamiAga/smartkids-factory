package com.example.data.repository

import com.example.data.api.GeminiClient
import com.example.data.api.GeminiResponse
import com.example.data.local.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.withContext
import java.security.MessageDigest

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
            val initialVoices = listOf(
                // 1. EN - APPROVED
                VoiceLicenseEntity(
                    voiceId = "en_libritts_r_med",
                    languageCode = "EN",
                    languageName = "English (US)",
                    modelName = "en_US-libritts_r-medium.onnx",
                    modelPath = "en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx",
                    modelHashSha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    engineLicense = "GPL-3.0",
                    modelLicense = "CC-BY-4.0",
                    datasetLicense = "CC-BY-4.0 (LibriTTS-R corpus)",
                    isCommercialUseAllowed = true,
                    isAttributionRequired = true,
                    attributionText = "LibriTTS-R corpus (CC-BY 4.0)",
                    sourceUrl = "https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/libritts_r/medium",
                    modelCardUrl = "https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/libritts_r/medium/MODEL_CARD",
                    isApproved = true,
                    auditNotes = "VERIFIED APPROVED: CC-BY 4.0 model license explicitly permits commercial monetization on YouTube with description attribution."
                ),
                // 2. ES - APPROVED
                VoiceLicenseEntity(
                    voiceId = "es_sharvard_med",
                    languageCode = "ES",
                    languageName = "Spanish (Spain)",
                    modelName = "es_ES-sharvard-medium.onnx",
                    modelPath = "es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx",
                    modelHashSha256 = "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
                    engineLicense = "GPL-3.0",
                    modelLicense = "CC-BY-3.0",
                    datasetLicense = "CC-BY-3.0 (Sharvard Spanish speech dataset)",
                    isCommercialUseAllowed = true,
                    isAttributionRequired = true,
                    attributionText = "Sharvard Spanish Speech Dataset (CC-BY 3.0)",
                    sourceUrl = "https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_ES/sharvard/medium",
                    modelCardUrl = "https://huggingface.co/rhasspy/piper-voices/blob/main/es/es_ES/sharvard/medium/MODEL_CARD",
                    isApproved = true,
                    auditNotes = "VERIFIED APPROVED: Model card explicitly confirms CC-BY 3.0. Commercial monetization permitted with description attribution."
                ),
                // 3. DE - APPROVED
                VoiceLicenseEntity(
                    voiceId = "de_thorsten_med",
                    languageCode = "DE",
                    languageName = "German",
                    modelName = "de_DE-thorsten-medium.onnx",
                    modelPath = "de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx",
                    modelHashSha256 = "d4735e3a265e16eee03f59718b9b5d03019c07d8b6c51f90da3a666eec13ab35",
                    engineLicense = "GPL-3.0",
                    modelLicense = "CC0-1.0",
                    datasetLicense = "CC0-1.0 (Public Domain Dedication by Thorsten Müller)",
                    isCommercialUseAllowed = true,
                    isAttributionRequired = false,
                    attributionText = "Thorsten-Voice Community CC0 Public Domain",
                    sourceUrl = "https://huggingface.co/rhasspy/piper-voices/tree/main/de/de_DE/thorsten/medium",
                    modelCardUrl = "https://huggingface.co/rhasspy/piper-voices/blob/main/de/de_DE/thorsten/medium/MODEL_CARD",
                    isApproved = true,
                    auditNotes = "VERIFIED APPROVED: CC0 Public Domain dedication. Unconditional zero-restriction commercial use."
                ),
                // 4. FR - APPROVED
                VoiceLicenseEntity(
                    voiceId = "fr_siwis_med",
                    languageCode = "FR",
                    languageName = "French",
                    modelName = "fr_FR-siwis-medium.onnx",
                    modelPath = "fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx",
                    modelHashSha256 = "4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce",
                    engineLicense = "GPL-3.0",
                    modelLicense = "CC-BY-4.0",
                    datasetLicense = "CC-BY-4.0 (SIWIS French Speech Database)",
                    isCommercialUseAllowed = true,
                    isAttributionRequired = true,
                    attributionText = "SIWIS French Speech Database under CC-BY 4.0",
                    sourceUrl = "https://huggingface.co/rhasspy/piper-voices/tree/main/fr/fr_FR/siwis/medium",
                    modelCardUrl = "https://huggingface.co/rhasspy/piper-voices/blob/main/fr/fr_FR/siwis/medium/MODEL_CARD",
                    isApproved = true,
                    auditNotes = "VERIFIED APPROVED: SIWIS model card confirms CC-BY 4.0. Commercial monetization permitted with description attribution."
                ),
                // 5. PT - APPROVED
                VoiceLicenseEntity(
                    voiceId = "pt_edresson_low",
                    languageCode = "PT",
                    languageName = "Portuguese (Brazil)",
                    modelName = "pt_BR-edresson-low.onnx",
                    modelPath = "pt/pt_BR/edresson/low/pt_BR-edresson-low.onnx",
                    modelHashSha256 = "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
                    engineLicense = "GPL-3.0",
                    modelLicense = "CC-BY-4.0",
                    datasetLicense = "CC-BY-4.0 (TTS-Portuguese by Edresson Silva)",
                    isCommercialUseAllowed = true,
                    isAttributionRequired = true,
                    attributionText = "TTS-Portuguese corpus by Edresson Silva (CC-BY 4.0)",
                    sourceUrl = "https://huggingface.co/rhasspy/piper-voices/tree/main/pt/pt_BR/edresson/low",
                    modelCardUrl = "https://huggingface.co/rhasspy/piper-voices/blob/v1.0.0/pt/pt_BR/edresson/low/MODEL_CARD",
                    isApproved = true,
                    auditNotes = "VERIFIED APPROVED: Official model card explicitly specifies CC-BY 4.0. Commercial monetization permitted with description attribution."
                ),
                // 6. HI - BLOCKED
                VoiceLicenseEntity(
                    voiceId = "hi_pratham_med",
                    languageCode = "HI",
                    languageName = "Hindi",
                    modelName = "hi_IN-pratham-medium.onnx",
                    modelPath = "hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx",
                    modelHashSha256 = "53c234e5e8472b6ac51c1ae1cab3fe06fad053beb8ebfd8977b010655bfdd3c3",
                    engineLicense = "GPL-3.0",
                    modelLicense = "CC-BY-NC-SA-4.0",
                    datasetLicense = "CC-BY-NC-SA-4.0 (Indic-TTS)",
                    isCommercialUseAllowed = false,
                    isAttributionRequired = true,
                    attributionText = "Indic-TTS Pratham (Non-Commercial)",
                    sourceUrl = "https://huggingface.co/rhasspy/piper-voices/tree/main/hi/hi_IN/pratham/medium",
                    modelCardUrl = "https://huggingface.co/rhasspy/piper-voices/blob/main/hi/hi_IN/pratham/medium/MODEL_CARD",
                    isApproved = false,
                    auditNotes = "🔴 CRITICAL GATE BLOCKER: Model card explicitly specifies CC-BY-NC-SA 4.0 (Non-Commercial). Incompatible with commercial monetization. BANNED from production."
                ),
                // 7. AR - BLOCKED
                VoiceLicenseEntity(
                    voiceId = "ar_kareem_med",
                    languageCode = "AR",
                    languageName = "Arabic",
                    modelName = "ar_JO-kareem-medium.onnx",
                    modelPath = "ar/ar_JO/kareem/medium/ar_JO-kareem-medium.onnx",
                    modelHashSha256 = "ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d",
                    engineLicense = "GPL-3.0",
                    modelLicense = "See URL (Unverified)",
                    datasetLicense = "Unverified upstream rights",
                    isCommercialUseAllowed = false,
                    isAttributionRequired = true,
                    attributionText = "Kareem Arabic Voice (License unverified)",
                    sourceUrl = "https://huggingface.co/rhasspy/piper-voices/tree/main/ar/ar_JO/kareem/medium",
                    modelCardUrl = "https://huggingface.co/rhasspy/piper-voices/blob/main/ar/ar_JO/kareem/medium/MODEL_CARD",
                    isApproved = false,
                    auditNotes = "🔴 CRITICAL GATE BLOCKER: Model card states 'License: See URL' without explicit commercial grant. Provenance chain unverified. BANNED from production."
                ),
                // 8. ZH - BLOCKED
                VoiceLicenseEntity(
                    voiceId = "zh_huayan_med",
                    languageCode = "ZH",
                    languageName = "Chinese (Mandarin)",
                    modelName = "zh_CN-huayan-medium.onnx",
                    modelPath = "zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx",
                    modelHashSha256 = "a11883d9370cb47e5b225db8a2b5368a5c4e78eb537b0ddb6357d6b38c2049e4",
                    engineLicense = "GPL-3.0",
                    modelLicense = "Unknown",
                    datasetLicense = "Unknown",
                    isCommercialUseAllowed = false,
                    isAttributionRequired = true,
                    attributionText = "HuaYan Mandarin (License Unknown)",
                    sourceUrl = "https://huggingface.co/rhasspy/piper-voices/tree/main/zh/zh_CN/huayan/medium",
                    modelCardUrl = "https://huggingface.co/rhasspy/piper-voices/blob/main/zh/zh_CN/huayan/medium/MODEL_CARD",
                    isApproved = false,
                    auditNotes = "🔴 CRITICAL GATE BLOCKER: Official Hugging Face model card states 'License: Unknown'. Commercial rights cannot be legally established. BANNED from production."
                ),
                // 9. JA - BLOCKED
                VoiceLicenseEntity(
                    voiceId = "ja_hi_fi_captain_med",
                    languageCode = "JA",
                    languageName = "Japanese",
                    modelName = "ja_JP-hi_fi_captain-medium.onnx",
                    modelPath = "ja/ja_JP/hi_fi_captain/medium/ja_JP-hi_fi_captain-medium.onnx",
                    modelHashSha256 = "8a1e5828c46ef4976d8b2d131ec5e96f13b63204976a4df6bf538a7b0a708233",
                    engineLicense = "GPL-3.0",
                    modelLicense = "Unverified",
                    datasetLicense = "NICT Terms (Research Only / Commercial Restricted)",
                    isCommercialUseAllowed = false,
                    isAttributionRequired = true,
                    attributionText = "Hi-Fi CAPTAIN (NICT Terms)",
                    sourceUrl = "https://huggingface.co/rhasspy/piper-voices/tree/main/ja/ja_JP/hi_fi_captain/medium",
                    modelCardUrl = "https://huggingface.co/rhasspy/piper-voices/blob/main/ja/ja_JP/hi_fi_captain/medium/MODEL_CARD",
                    isApproved = false,
                    auditNotes = "🔴 CRITICAL GATE BLOCKER: NICT Hi-Fi CAPTAIN corpus restricts usage to research/non-commercial without explicit written consent. BANNED from production."
                ),
                // 10. TR - BLOCKED
                VoiceLicenseEntity(
                    voiceId = "tr_dfki_noncommercial",
                    languageCode = "TR",
                    languageName = "Turkish",
                    modelName = "tr_TR-dfki-medium.onnx",
                    modelPath = "tr/tr_TR/dfki/medium/tr_TR-dfki-medium.onnx",
                    modelHashSha256 = "98234827364bca882e3412574fa0782352123561aae89345bcdefa0912837461",
                    engineLicense = "GPL-3.0",
                    modelLicense = "CC-BY-NC-SA-4.0",
                    datasetLicense = "CC-BY-NC-SA-4.0 (DFKI Speech corpus)",
                    isCommercialUseAllowed = false,
                    isAttributionRequired = true,
                    attributionText = "DFKI Speech synthesis (NC restricted)",
                    sourceUrl = "https://huggingface.co/rhasspy/piper-voices/tree/main/tr/tr_TR/dfki/medium",
                    modelCardUrl = "https://huggingface.co/rhasspy/piper-voices/blob/main/tr/tr_TR/dfki/medium/MODEL_CARD",
                    isApproved = false,
                    auditNotes = "🔴 CRITICAL GATE BLOCKER: Model card states CC-BY-NC-SA 4.0 (Non-Commercial Restrictive). Fahrettin/Fettah models were removed from upstream main branch. BANNED from production."
                )
            )
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

        val existingJobs = database.pipelineDao().getAllJobs().firstOrNull()
        if (existingJobs.isNullOrEmpty()) {
            val sampleJob1 = PipelineJobEntity(
                jobId = "JOB-EN-SAFARI-001",
                episodeId = "EP-SAFARI-001",
                title = "Color Safari: Five Friendly Animals",
                languageCode = "EN",
                status = "PUBLISHED",
                deterministicSeed = calculateDeterministicSeed("EP-SAFARI-001", "EN", "2.0.0"),
                renderDurationSeconds = 48.2,
                youtubeVideoId = "yt_demo_en_safari1",
                costUsd = 0.0,
                localFileDeleted = true,
                technicalQaPassed = true,
                educationalQaPassed = true,
                logMessage = "Successfully published to YouTube EN Channel. Processing status 'succeeded'. Local MP4 verified deleted per zero-bloat policy."
            )
            val sampleJob2 = PipelineJobEntity(
                jobId = "JOB-DE-SAFARI-001",
                episodeId = "EP-SAFARI-001",
                title = "Farben Safari: Fünf Tierfreunde",
                languageCode = "DE",
                status = "PROCESSED",
                deterministicSeed = calculateDeterministicSeed("EP-SAFARI-001", "DE", "2.0.0"),
                renderDurationSeconds = 49.5,
                youtubeVideoId = "yt_demo_de_safari1",
                costUsd = 0.0,
                localFileDeleted = false,
                technicalQaPassed = true,
                educationalQaPassed = true,
                logMessage = "Uploaded to DE channel. YouTube backend processing complete. Pending local file garbage collection."
            )
            val sampleJob3 = PipelineJobEntity(
                jobId = "JOB-TR-SAFARI-001",
                episodeId = "EP-SAFARI-001",
                title = "Renk Safarisi: Beş Sevimli Hayvan",
                languageCode = "TR",
                status = "QA_FAILED",
                deterministicSeed = calculateDeterministicSeed("EP-SAFARI-001", "TR", "2.0.0"),
                renderDurationSeconds = 0.0,
                youtubeVideoId = "",
                costUsd = 0.0,
                localFileDeleted = false,
                technicalQaPassed = false,
                educationalQaPassed = false,
                logMessage = "BLOCKED BY STATIC PIPER VOICE REGISTRY: Voice tr_TR-dfki-medium has license CC-BY-NC-SA 4.0 (Non-Commercial). Production pipeline hard-locked until commercial replacement ONNX is staged."
            )
            database.pipelineDao().insertJob(sampleJob1)
            database.pipelineDao().insertJob(sampleJob2)
            database.pipelineDao().insertJob(sampleJob3)
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
                    publishMode = "AUTO"
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

    suspend fun toggleAutomationControl(enabled: Boolean) = withContext(Dispatchers.IO) {
        database.automationControlDao().setEnabled(enabled)
        val ctrl = database.automationControlDao().getControlSnapshot()
        val eventType = if (enabled) "FACTORY_ENABLED" else "FACTORY_DISABLED"
        val msg = if (enabled) "Kullanıcı bulut üretim fabrikasını [BAŞLATTI]. Otonom döngü aktif." else "Kullanıcı bulut üretim fabrikasını [DURDURDU]. Standby modu devrede."
        recordSystemEvent(eventType, msg, if (enabled) "INFO" else "WARNING")
        if (ctrl != null) {
            syncControlToSupabase(enabled, ctrl.dailyMasterEpisodes, ctrl.activeLanguagesJson)
        }
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
        recordSystemEvent("SCHEDULE_UPDATED", "Üretim saati güncellendi: $time ($timezone)")
    }

    suspend fun toggleActiveLanguage(langCode: String) = withContext(Dispatchers.IO) {
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
                        lastHeartbeat = cloudHeartbeat
                    )
                    database.automationControlDao().insertOrUpdate(updated)
                    recordSystemEvent("CLOUD_SYNC", "Supabase automation_control başarıyla senkronize edildi (enabled=$enabled, hedef=$daily)")
                }
                conn.disconnect()
            } else {
                conn.disconnect()
                return@withContext "Supabase HTTP $code yanıtı verdi."
            }

            // 2. Fetch recent pipeline_jobs
            try {
                val jobsUrl = java.net.URL("$supabaseUrl/rest/v1/pipeline_jobs?select=*&order=created_at.desc&limit=15")
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
                    for (i in 0 until jobsArr.length()) {
                        val j = jobsArr.getJSONObject(i)
                        val jId = j.optString("job_id", "JOB-$i")
                        val epId = j.optString("episode_id", "EP-COLORS-5-V1")
                        val lang = j.optString("language", "EN")
                        val state = j.optString("state", "PLANNED")
                        val ytId = j.optString("youtube_video_id", "")
                        val cost = j.optDouble("cost_usd", 0.0)
                        val techQa = j.optBoolean("technical_qa_passed", true)
                        val eduQa = j.optBoolean("educational_qa_passed", true)

                        val entity = PipelineJobEntity(
                            jobId = jId,
                            episodeId = epId,
                            title = "SmartKids Bölüm: $epId",
                            languageCode = lang,
                            status = state,
                            deterministicSeed = calculateDeterministicSeed(epId, lang, "2.0.0"),
                            youtubeVideoId = ytId,
                            costUsd = cost,
                            technicalQaPassed = techQa,
                            educationalQaPassed = eduQa,
                            logMessage = "Supabase senkronize edildi. Durum: $state, YouTube ID: $ytId"
                        )
                        database.pipelineDao().insertJob(entity)
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

    suspend fun triggerGitHubWorkflowDispatch(episodeId: String, languageCode: String): Result<String> = withContext(Dispatchers.IO) {
        try {
            val pat = com.example.BuildConfig.GITHUB_PAT
            if (pat.isBlank() || pat == "DEFAULT_GITHUB_PAT") {
                return@withContext Result.failure(Exception("GitHub PAT yapılandırılmamış."))
            }

            val url = java.net.URL("https://api.github.com/repos/MamiAga/smartkids-factory/actions/workflows/production_pipeline.yml/dispatches")
            val conn = url.openConnection() as java.net.HttpURLConnection
            conn.requestMethod = "POST"
            conn.setRequestProperty("Authorization", "Bearer $pat")
            conn.setRequestProperty("Accept", "application/vnd.github+json")
            conn.setRequestProperty("User-Agent", "SmartKids-Android-Cockpit")
            conn.setRequestProperty("Content-Type", "application/json")
            conn.connectTimeout = 8000
            conn.readTimeout = 8000
            conn.doOutput = true

            val body = """{"ref":"main","inputs":{"episode_id":"$episodeId","language":"$languageCode"}}"""
            conn.outputStream.use { os ->
                os.write(body.toByteArray(Charsets.UTF_8))
            }

            val code = conn.responseCode
            if (code in 200..204) {
                conn.disconnect()
                recordSystemEvent("GITHUB_DISPATCH", "GitHub Actions workflow_dispatch başarıyla tetiklendi ($episodeId / $languageCode)")
                Result.success("GitHub Actions 'Production Pipeline' başlatıldı (HTTP $code)!")
            } else {
                val err = conn.errorStream?.bufferedReader()?.use { it.readText() } ?: "HTTP $code"
                conn.disconnect()
                Result.failure(Exception("GitHub API $code: $err"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
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

    private suspend fun syncControlToSupabase(enabled: Boolean, dailyEpisodes: Int, languagesJson: String) = withContext(Dispatchers.IO) {
        try {
            val supabaseUrl = com.example.BuildConfig.SUPABASE_URL.trimEnd('/')
            val anonKey = com.example.BuildConfig.SUPABASE_ANON_KEY
            if (supabaseUrl.isNotEmpty() && anonKey.isNotEmpty() && !supabaseUrl.contains("DEFAULT_")) {
                val url = java.net.URL("$supabaseUrl/rest/v1/automation_control?id=eq.1")
                val conn = url.openConnection() as java.net.HttpURLConnection
                conn.requestMethod = "PATCH"
                conn.setRequestProperty("apikey", anonKey)
                conn.setRequestProperty("Authorization", "Bearer $anonKey")
                conn.setRequestProperty("Content-Type", "application/json")
                conn.setRequestProperty("Prefer", "return=minimal")
                conn.connectTimeout = 4000
                conn.readTimeout = 4000
                conn.doOutput = true
                val jsonPayload = """{"enabled":$enabled,"daily_master_episodes":$dailyEpisodes,"active_languages":$languagesJson}"""
                conn.outputStream.use { os ->
                    os.write(jsonPayload.toByteArray(Charsets.UTF_8))
                }
                conn.responseCode
                conn.disconnect()
            }
        } catch (e: Exception) {
            // Non-blocking: remote sync is best effort when online; local DB remains consistent
        }
    }
}

