package com.example.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.data.api.GeminiClient
import com.example.data.local.*
import com.example.data.repository.SmartKidsRepository
import com.example.data.worker.YouTubeUploadStateMachine
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

enum class AppTab(val title: String) {
    CONTROL_CENTER("Fabrika Kumandası"),
    PIPELINE("İş Akışı"),
    EPISODE_DNA("Bölüm DNA"),
    VOICE_REGISTRY("Ses Lisansları"),
    AI_ARCHITECT("Fabrika Asistanı")
}

data class UiNotification(
    val message: String,
    val isError: Boolean = false
)

class MainViewModel(application: Application) : AndroidViewModel(application) {
    private val database = SmartKidsDatabase.getDatabase(application)
    private val repository = SmartKidsRepository(database)

    private val _currentTab = MutableStateFlow(AppTab.CONTROL_CENTER)
    val currentTab: StateFlow<AppTab> = _currentTab.asStateFlow()

    val voices: StateFlow<List<VoiceLicenseEntity>> = repository.allVoices
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val episodes: StateFlow<List<EpisodeDnaEntity>> = repository.allEpisodes
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val jobs: StateFlow<List<PipelineJobEntity>> = repository.allJobs
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val chatMessages: StateFlow<List<ChatMessageEntity>> = repository.allChatMessages
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val unapprovedOrBlockedCount: StateFlow<Int> = repository.unapprovedOrBlockedCount
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), 0)

    val automationControl: StateFlow<AutomationControlEntity?> = repository.automationControl
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    val systemEvents: StateFlow<List<SystemEventEntity>> = repository.systemEvents
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Chatbot UI state: gemini-3.5-flash (Architect/QA) or gemini-3.5-flash-lite (Localization/Metadata)
    private val _chatInput = MutableStateFlow("")
    val chatInput: StateFlow<String> = _chatInput.asStateFlow()

    private val _selectedChatModel = MutableStateFlow(GeminiClient.MODEL_FLASH)
    val selectedChatModel: StateFlow<String> = _selectedChatModel.asStateFlow()

    private val _isAiLoading = MutableStateFlow(false)
    val isAiLoading: StateFlow<Boolean> = _isAiLoading.asStateFlow()

    private val _notification = MutableStateFlow<UiNotification?>(null)
    val notification: StateFlow<UiNotification?> = _notification.asStateFlow()

    // Episode DNA inspection / QA
    private val _selectedEpisode = MutableStateFlow<EpisodeDnaEntity?>(null)
    val selectedEpisode: StateFlow<EpisodeDnaEntity?> = _selectedEpisode.asStateFlow()

    private val _qaResult = MutableStateFlow<String?>(null)
    val qaResult: StateFlow<String?> = _qaResult.asStateFlow()

    // Static Audit Inspection Modal / Dialog
    private val _inspectedVoiceAudit = MutableStateFlow<String?>(null)
    val inspectedVoiceAudit: StateFlow<String?> = _inspectedVoiceAudit.asStateFlow()

    // Cloud Connectivity Diagnostics State
    private val cloudDiagnostics = com.example.data.remote.CloudConnectivityDiagnostics()
    private val _diagnosticsState = MutableStateFlow<com.example.data.remote.FullDiagnosticsResult?>(null)
    val diagnosticsState: StateFlow<com.example.data.remote.FullDiagnosticsResult?> = _diagnosticsState.asStateFlow()

    private val _isDiagnosing = MutableStateFlow(false)
    val isDiagnosing: StateFlow<Boolean> = _isDiagnosing.asStateFlow()

    private val _isSyncing = MutableStateFlow(false)
    val isSyncing: StateFlow<Boolean> = _isSyncing.asStateFlow()

    fun syncFromSupabase() {
        if (_isSyncing.value) return
        viewModelScope.launch {
            _isSyncing.value = true
            _notification.value = UiNotification("Supabase ile canlı veriler senkronize ediliyor...")
            val result = repository.syncFromSupabaseCloud()
            _isSyncing.value = false
            _notification.value = UiNotification(result)
        }
    }

    fun runConnectivityDiagnostics() {
        if (_isDiagnosing.value) return
        viewModelScope.launch {
            _isDiagnosing.value = true
            _notification.value = UiNotification("Bulut servisleri (Supabase, GitHub, YouTube) test ediliyor...")
            val result = cloudDiagnostics.runFullDiagnostics()
            _diagnosticsState.value = result
            _isDiagnosing.value = false
            _notification.value = UiNotification(
                result.summaryMessage,
                isError = !result.allHealthy
            )
        }
    }

    fun dismissDiagnosticsDialog() {
        _diagnosticsState.value = null
    }

    init {
        viewModelScope.launch {
            repository.initializeDatabaseDefaults()
            try {
                repository.syncFromSupabaseCloud()
            } catch (e: Exception) {
                // Initial sync best effort
            }
        }
        viewModelScope.launch {
            while (true) {
                kotlinx.coroutines.delay(15_000)
                try {
                    repository.syncFromSupabaseCloud()
                } catch (e: Exception) {
                    // Periodic background sync best effort
                }
            }
        }
    }

    fun selectTab(tab: AppTab) {
        _currentTab.value = tab
    }

    fun setChatInput(text: String) {
        _chatInput.value = text
    }

    fun setSelectedChatModel(model: String) {
        _selectedChatModel.value = if (model == GeminiClient.MODEL_FLASH_LITE) GeminiClient.MODEL_FLASH_LITE else GeminiClient.MODEL_FLASH
    }

    fun clearNotification() {
        _notification.value = null
    }

    fun inspectVoiceStaticAudit(voice: VoiceLicenseEntity) {
        val auditRecord = repository.verifyVoiceStaticAudit(voice)
        _inspectedVoiceAudit.value = auditRecord
    }

    fun clearInspectedVoiceAudit() {
        _inspectedVoiceAudit.value = null
    }

    fun toggleVoiceApproval(voice: VoiceLicenseEntity) {
        viewModelScope.launch {
            if (!voice.isCommercialUseAllowed && !voice.isApproved) {
                _notification.value = UiNotification(
                    "⚠️ GÜVENLİK KAPISI: '${voice.modelName}' onaylanamaz çünkü ticari kullanım izni yok (${voice.modelLicense}). Ticari olmayan lisans ihlali kesinlikle yasaktır!",
                    isError = true
                )
                return@launch
            }
            val newApproval = !voice.isApproved
            repository.setVoiceApproval(voice.voiceId, newApproval)
            _notification.value = UiNotification(
                if (newApproval) "${voice.languageCode} sesi üretim için onaylandı." else "${voice.languageCode} sesi onayı kaldırıldı."
            )
        }
    }

    fun selectEpisode(episode: EpisodeDnaEntity?) {
        _selectedEpisode.value = episode
        _qaResult.value = null
    }

    fun runEducationalQa(episode: EpisodeDnaEntity) {
        viewModelScope.launch {
            _isAiLoading.value = true
            val response = repository.performEducationalQa(episode)
            _isAiLoading.value = false
            _qaResult.value = response.text
            val updated = episode.copy(
                qaStatus = if (response.text.contains("PASSED", ignoreCase = true)) "PASSED_QA" else "FAILED_QA"
            )
            repository.saveEpisode(updated)
            _selectedEpisode.value = updated
        }
    }

    fun generateNewEpisodeDna(topicPrompt: String) {
        viewModelScope.launch {
            _isAiLoading.value = true
            val prompt = """
                Generate a new production-ready Episode DNA for SmartKids:
                Topic: $topicPrompt
                Format: Output strict valid JSON matching EpisodeDNA schema:
                {
                   "title": "string",
                   "age_group": "2-4" or "4-6" or "6-8",
                   "format_type": "Nursery Rhyme" or "Counting" or "Concept Exploration" or "Interactive Quiz",
                   "learning_objective": "string",
                   "difficulty": "Beginner",
                   "target_duration_seconds": 120,
                   "characters": [{"id":"char1","name":"Name","role":"Role"}],
                   "visual_style": "string",
                   "music_profile": "string",
                   "scenes": [{"scene_number":1,"name":"Intro","speech":"...","visual_items":1}],
                   "safety_profile": "string"
                }
            """.trimIndent()

            val response = repository.sendChatMessage(
                userMessage = prompt,
                model = GeminiClient.MODEL_FLASH
            )
            _isAiLoading.value = false

            val id = "EP-GEN-${System.currentTimeMillis() % 10000}"
            val newEp = EpisodeDnaEntity(
                episodeId = id,
                title = "Müfredat: $topicPrompt",
                ageGroup = "2-4",
                formatType = "Concept Exploration",
                learningObjective = "$topicPrompt için temel kavram eğitimi",
                difficulty = "Beginner",
                targetDurationSeconds = 120,
                minDurationSeconds = 110,
                maxDurationSeconds = 130,
                charactersJson = """[{"id":"ai_tutor","name":"Tutor Spark","role":"Guide"}]""",
                visualStyle = "Deterministik pastel SVG/FFmpeg 60fps",
                musicProfile = "Sakin marimba 100 BPM",
                scenesJson = """[{"scene_number":1,"name":"Giriş","speech":"Hadi birlikte $topicPrompt öğrenelim!","visual_items":1}]""",
                safetyProfile = "Sıfır flaş/parlama, yumuşak kontrast, 2.0sn etkileşim duraklaması",
                qaStatus = "PENDING_QA"
            )
            repository.saveEpisode(newEp)
            _selectedEpisode.value = newEp
            _notification.value = UiNotification("gemini-3.5-flash ile Bölüm DNA'sı ($id) oluşturuldu.")
        }
    }

    /**
     * Previously this advanced the job locally through fake states (fake "yt_*" video ids, fake
     * "Oracle 200GB" logs). Job states are now written ONLY by the cloud runner into Supabase;
     * the phone just displays them.
     */
    fun stepPipelineJob(job: PipelineJobEntity) {
        _notification.value = UiNotification(
            "${job.jobId}: aşamalar bulutta (GitHub Actions) ilerler; telefondan elle ilerletilemez. Durum: ${job.status}"
        )
        syncFromSupabase()
    }

    fun dispatchProductionWorkflow(episodeId: String, languageCode: String) {
        viewModelScope.launch {
            _isSyncing.value = true
            _notification.value = UiNotification("GitHub Actions tek iş tetikleniyor ($episodeId, $languageCode)...")
            val result = repository.triggerGitHubWorkflowDispatch(episodeId, languageCode)
            _notification.value = if (result.isSuccess) {
                UiNotification("✅ Tek iş tetiklendi. Gerçek durum Supabase'ten birkaç dakika içinde gelecek (zaten yüklendiyse tekrar yüklenmez).")
            } else {
                UiNotification("❌ GitHub tetikleme hatası: ${result.exceptionOrNull()?.message}", isError = true)
            }
            _isSyncing.value = false
            repository.syncFromSupabaseCloud()
        }
    }

    fun createPipelineJobForLanguage(episode: EpisodeDnaEntity, languageCode: String) {
        viewModelScope.launch {
            // Check if voice is approved & commercial safe
            val voice = repository.allVoices.firstOrNull()?.find { it.languageCode == languageCode }
            if (voice == null || !voice.isCommercialUseAllowed || !voice.isApproved) {
                val blockedJob = PipelineJobEntity(
                    jobId = "JOB-$languageCode-${episode.episodeId}-${System.currentTimeMillis() % 1000}",
                    episodeId = episode.episodeId,
                    title = "${episode.title} ($languageCode)",
                    languageCode = languageCode,
                    status = "QA_FAILED",
                    deterministicSeed = repository.calculateDeterministicSeed(episode.episodeId, languageCode, episode.version),
                    costUsd = 0.0,
                    logMessage = "ENGEL: $languageCode dili için ses onaylı değil veya ticari kullanım izni yok (${voice?.modelLicense ?: "Eksik Ses Modeli"})."
                )
                repository.saveJob(blockedJob)
                _notification.value = UiNotification("❌ Görev Ses Lisans Kütüğü güvenlik kapısı tarafından engellendi!", isError = true)
                return@launch
            }

            dispatchProductionWorkflow(episode.episodeId, languageCode)
        }
    }

    /**
     * START: Supabase enabled=true (must succeed) -> dispatch smartkids_factory.yml run_now=true.
     * STOP : Supabase enabled=false. The runner re-checks `enabled` before every job and before
     *        every upload, so STOP takes effect without the phone staying online.
     * Only ONE workflow is used for production, so START can no longer create two parallel
     * productions (old behaviour: production_pipeline dispatch + hourly factory both uploading).
     */
    fun toggleFactory(enabled: Boolean) {
        viewModelScope.launch {
            _isSyncing.value = true
            val ok = repository.toggleAutomationControl(enabled)
            if (!ok) {
                _notification.value = UiNotification(
                    "❌ Supabase'e yazılamadı (internet / RLS / anahtar). Fabrika durumu DEĞİŞMEDİ.",
                    isError = true
                )
                _isSyncing.value = false
                return@launch
            }
            if (enabled) {
                val result = repository.triggerFactoryRunNow()
                _notification.value = if (result.isSuccess) {
                    UiNotification("✅ ÜRETİM AÇIK. Bulut fabrikası şimdi tetiklendi; telefonu kapatabilirsiniz.")
                } else {
                    UiNotification(
                        "🟡 ÜRETİM AÇIK (Supabase). Anlık tetikleme başarısız: ${result.exceptionOrNull()?.message}. " +
                            "Saatlik zamanlayıcı en geç 1 saat içinde devralır.",
                        isError = true
                    )
                }
            } else {
                _notification.value = UiNotification("🔴 ÜRETİM KAPALI. Çalışan iş varsa bir sonraki adımda durur.")
            }
            repository.syncFromSupabaseCloud()
            _isSyncing.value = false
        }
    }

    private fun parseActiveLanguage(langsJson: String?): String {
        if (langsJson.isNullOrBlank()) return "EN"
        return try {
            val cleaned = langsJson.trim().removeSurrounding("[", "]")
            cleaned.split(",")
                .map { it.trim().removeSurrounding("\"") }
                .firstOrNull { it.isNotEmpty() } ?: "EN"
        } catch (e: Exception) {
            "EN"
        }
    }

    fun updateDailyTarget(episodes: Int) {
        viewModelScope.launch {
            repository.updateDailyMasterEpisodes(episodes)
            _notification.value = UiNotification("Günlük hedef $episodes master bölüm olarak güncellendi.")
        }
    }

    fun updateSchedule(time: String, timezone: String) {
        viewModelScope.launch {
            repository.updateSchedule(time, timezone)
            _notification.value = UiNotification("Zamanlama $time ($timezone) olarak kaydedildi.")
        }
    }

    fun toggleActiveLanguage(lang: String) {
        viewModelScope.launch {
            repository.toggleActiveLanguage(lang)
            _notification.value = UiNotification("Aktif dil seçimi güncellendi: $lang")
        }
    }

    fun sendChat() {
        val text = _chatInput.value.trim()
        if (text.isEmpty()) return
        _chatInput.value = ""
        viewModelScope.launch {
            _isAiLoading.value = true

            // Fast-path local command parsing for Factory Kumanda commands
            val lower = text.lowercase()
            if (lower.contains("üretimi başlat") || lower.contains("fabrikayı başlat") || lower == "başlat") {
                toggleFactory(true)
                repository.sendChatMessage(
                    userMessage = text,
                    model = _selectedChatModel.value
                )
            } else if (lower.contains("üretimi durdur") || lower.contains("fabrikayı durdur") || lower == "durdur") {
                toggleFactory(false)
                repository.sendChatMessage(
                    userMessage = text,
                    model = _selectedChatModel.value
                )
            } else {
                val response = repository.sendChatMessage(
                    userMessage = text,
                    model = _selectedChatModel.value
                )
                if (!response.isSuccess && response.errorMessage != null) {
                    _notification.value = UiNotification("Gemini: ${response.errorMessage}", isError = true)
                }
            }
            _isAiLoading.value = false
        }
    }

    fun clearChat() {
        viewModelScope.launch {
            repository.clearChatHistory()
            _notification.value = UiNotification("Chat history cleared.")
        }
    }
}
