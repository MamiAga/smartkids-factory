package com.example.data.worker

import android.util.Log

/**
 * YouTube Upload State Machine
 *
 * Tracks video upload lifecycle in the autonomous pipeline:
 * Happy path: RENDERED -> UPLOADING -> UPLOADED -> PROCESSING -> PROCESSED -> PUBLISHED -> DELETE_LOCAL_FILE -> ARCHIVED_ZERO_BLOAT
 * Failure states: AUTH_FAILED, QUOTA_PAUSED, PROCESSING_FAILED, QA_FAILED
 *
 * Enforces zero-disk-leak policy: Local MP4 cannot be deleted until YouTube processing is PROCESSED and DB committed.
 */
class YouTubeUploadStateMachine(
    private val jobId: String,
    initialStatus: UploadStatus = UploadStatus.RENDERED,
    private val onStateChanged: ((oldStatus: UploadStatus, newStatus: UploadStatus, log: String) -> Unit)? = null
) {
    companion object {
        private const val TAG = "YouTubeUploadStateMachine"
    }

    enum class UploadStatus(val isTerminal: Boolean, val isError: Boolean, val descriptionTr: String) {
        RENDERED(false, false, "Video deterministik renderlandı, yüklemeye hazır"),
        UPLOADING(false, false, "YouTube API üzerinden parçalı yükleme (resumable) devam ediyor"),
        UPLOADED(false, false, "Yükleme tamamlandı, video ID alındı"),
        PROCESSING(false, false, "YouTube arka plan video işleme kontrolü yapılıyor (polling)"),
        PROCESSED(false, false, "YouTube video işleme başarıyla tamamlandı"),
        PUBLISHED(false, false, "Video yayınlandı, kanal listesinde aktif"),
        DELETE_LOCAL_FILE(false, false, "Yerel MP4 silindi (0 bayt disk sızıntısı kuralı uygulandı)"),
        ARCHIVED_ZERO_BLOAT(true, false, "İşlem başarıyla arşivlendi, disk temiz"),
        
        // Hata Durumları (Failure States)
        AUTH_FAILED(true, true, "YouTube OAuth yetkilendirmesi başarısız (refresh_token geçersiz)"),
        QUOTA_PAUSED(false, true, "Günlük YouTube API kotası aşıldı (100 insert/gün). Gece yarısına kadar duraklatıldı"),
        PROCESSING_FAILED(true, true, "YouTube video işleme hatası (telif, çözünürlük veya format reddi)"),
        QA_FAILED(true, true, "Kalite kontrol denetimi başarısız oldu (ses lisansı veya eğitsel tutarsızlık)")
    }

    var currentStatus: UploadStatus = initialStatus
        private set

    val history = mutableListOf<StateTransition>()

    data class StateTransition(
        val fromStatus: UploadStatus,
        val toStatus: UploadStatus,
        val timestamp: Long = System.currentTimeMillis(),
        val message: String
    )

    /**
     * Attempts a transition to the target state.
     * Validates state machine rules and prevents illegal transitions.
     */
    fun transitionTo(targetStatus: UploadStatus, reason: String = ""): Boolean {
        val oldStatus = currentStatus
        if (!isValidTransition(oldStatus, targetStatus)) {
            val errorMsg = "GEÇERSİZ GEÇİŞ: $oldStatus durumundan $targetStatus durumuna geçilemez! (İş: $jobId)"
            Log.e(TAG, errorMsg)
            return false
        }

        currentStatus = targetStatus
        val transition = StateTransition(
            fromStatus = oldStatus,
            toStatus = targetStatus,
            message = reason.ifBlank { targetStatus.descriptionTr }
        )
        history.add(transition)

        Log.i(TAG, "[$jobId] Durum güncellendi: $oldStatus -> $targetStatus | ${transition.message}")
        onStateChanged?.invoke(oldStatus, targetStatus, transition.message)
        return true
    }

    /**
     * Validates transition rules
     */
    private fun isValidTransition(from: UploadStatus, to: UploadStatus): Boolean {
        if (from == to) return true

        return when (from) {
            UploadStatus.RENDERED -> to in listOf(
                UploadStatus.UPLOADING,
                UploadStatus.AUTH_FAILED,
                UploadStatus.QUOTA_PAUSED,
                UploadStatus.QA_FAILED
            )
            UploadStatus.UPLOADING -> to in listOf(
                UploadStatus.UPLOADED,
                UploadStatus.AUTH_FAILED,
                UploadStatus.QUOTA_PAUSED,
                UploadStatus.PROCESSING_FAILED
            )
            UploadStatus.UPLOADED -> to in listOf(
                UploadStatus.PROCESSING,
                UploadStatus.PROCESSING_FAILED
            )
            UploadStatus.PROCESSING -> to in listOf(
                UploadStatus.PROCESSED,
                UploadStatus.PROCESSING_FAILED
            )
            UploadStatus.PROCESSED -> to in listOf(
                UploadStatus.PUBLISHED,
                UploadStatus.DELETE_LOCAL_FILE
            )
            UploadStatus.PUBLISHED -> to in listOf(
                UploadStatus.DELETE_LOCAL_FILE
            )
            UploadStatus.DELETE_LOCAL_FILE -> to in listOf(
                UploadStatus.ARCHIVED_ZERO_BLOAT
            )
            UploadStatus.QUOTA_PAUSED -> to in listOf(
                UploadStatus.UPLOADING,
                UploadStatus.RENDERED
            )
            UploadStatus.AUTH_FAILED,
            UploadStatus.PROCESSING_FAILED,
            UploadStatus.QA_FAILED -> to in listOf(
                UploadStatus.RENDERED // Yeniden deneme için RENDERED durumuna dönebilir
            )
            UploadStatus.ARCHIVED_ZERO_BLOAT -> false // Terminal durum
        }
    }

    fun handleAuthFailure(details: String) {
        val message = "YouTube OAuth doğrulaması başarısız oldu. Token yenilenmeli: $details"
        Log.e(TAG, "[$jobId] AUTH_FAILED: $message")
        transitionTo(UploadStatus.AUTH_FAILED, message)
    }

    fun handleQuotaExceeded(resetTimeEpochMs: Long = 0) {
        val message = "YouTube Günlük Kota Aşıldı (100 insert sınırı). Kuyruk duraklatıldı."
        Log.w(TAG, "[$jobId] QUOTA_PAUSED: $message")
        transitionTo(UploadStatus.QUOTA_PAUSED, message)
    }

    fun handleProcessingFailure(errorReason: String) {
        val message = "YouTube video işleme reddedildi: $errorReason"
        Log.e(TAG, "[$jobId] PROCESSING_FAILED: $message")
        transitionTo(UploadStatus.PROCESSING_FAILED, message)
    }

    /**
     * Sıfır sızıntı kuralı: Yerel MP4 sadece YouTube sunucusunda 'PROCESSED' veya 'PUBLISHED'
     * onaylandıktan sonra silinebilir.
     */
    fun canSafelyDeleteLocalFile(): Boolean {
        return currentStatus in listOf(
            UploadStatus.PROCESSED,
            UploadStatus.PUBLISHED,
            UploadStatus.DELETE_LOCAL_FILE,
            UploadStatus.ARCHIVED_ZERO_BLOAT
        )
    }
}
