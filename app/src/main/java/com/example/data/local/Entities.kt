package com.example.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "voice_registry")
data class VoiceLicenseEntity(
    @PrimaryKey val voiceId: String,
    val languageCode: String,            // EN, ES, DE, FR, PT, AR, HI, ZH, JA, TR
    val languageName: String,
    val modelName: String,
    val modelPath: String,
    val modelHashSha256: String,
    val engineLicense: String = "GPL-3.0", // Piper Engine C++ / ONNX Runtime
    val modelLicense: String,             // CC-BY-4.0, CC-BY-3.0, CC0-1.0, MIT, Unknown, CC-BY-NC-SA-4.0
    val datasetLicense: String,           // Source corpus license
    val isCommercialUseAllowed: Boolean,  // Strict boolean: true ONLY if explicitly permitted
    val isAttributionRequired: Boolean,
    val attributionText: String,
    val sourceUrl: String,
    val modelCardUrl: String,
    val isApproved: Boolean,              // Strict boolean: true ONLY if commercial_use == true AND verified
    val auditNotes: String
)

@Entity(tableName = "episode_dna")
data class EpisodeDnaEntity(
    @PrimaryKey val episodeId: String,
    val version: String = "2.0.0",
    val title: String,
    val ageGroup: String,                // 2-4, 4-6, 6-8
    val formatType: String,              // Nursery Rhyme, Counting, Concept Exploration, Interactive Quiz
    val learningObjective: String,
    val difficulty: String,              // Beginner, Intermediate
    val targetDurationSeconds: Int,
    val minDurationSeconds: Int,
    val maxDurationSeconds: Int,
    val charactersJson: String,
    val visualStyle: String,
    val musicProfile: String,
    val scenesJson: String,
    val safetyProfile: String,
    val qaStatus: String = "PENDING_QA", // PENDING_QA, PASSED_QA, FAILED_QA
    val createdAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "pipeline_jobs")
data class PipelineJobEntity(
    @PrimaryKey val jobId: String,
    val episodeId: String,
    val title: String,
    val languageCode: String,
    val status: String,                  // PLANNED, SCRIPTED, LOCALIZED, TTS_READY, RENDERED, QA_PASSED, UPLOADING, UPLOADED, PROCESSING, PROCESSED, PUBLISHED, LOCAL_DELETE_PENDING, COMPLETED, QA_FAILED, QUARANTINED
    val deterministicSeed: String,
    val renderDurationSeconds: Double = 0.0,
    val youtubeVideoId: String = "",
    val costUsd: Double = 0.0,            // Strictly 0.00
    val localFileDeleted: Boolean = false,
    val technicalQaPassed: Boolean = false,
    val educationalQaPassed: Boolean = false,
    val logMessage: String = "",
    val updatedAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "chat_messages")
data class ChatMessageEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val role: String,                    // user, model, system
    val content: String,
    val modelUsed: String,               // gemini-3.5-flash, gemini-3.5-flash-lite
    val isThinkingHigh: Boolean = false,
    val isSearchGrounded: Boolean = false,
    val searchSourcesJson: String = "",
    val timestamp: Long = System.currentTimeMillis()
)

@Entity(tableName = "automation_control")
data class AutomationControlEntity(
    @PrimaryKey val id: Int = 1,
    val enabled: Boolean = false,
    val dailyMasterEpisodes: Int = 1,
    val scheduleTime: String = "04:00",
    val timezone: String = "Europe/Istanbul",
    val activeLanguagesJson: String = "[\"EN\"]",
    val activeChannelsJson: String = "[\"EN\"]",
    val generationMode: String = "AUTONOMOUS",
    val publishMode: String = "AUTO",
    val lastHeartbeat: Long = System.currentTimeMillis(),
    val lastRunAt: Long? = null,
    val nextRunAt: Long? = null,
    val currentJobId: String? = null,
    val failureCount: Int = 0,
    val updatedAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "system_events")
data class SystemEventEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val eventType: String,
    val severity: String = "INFO",
    val message: String,
    val details: String = "",
    val timestamp: Long = System.currentTimeMillis()
)
