package com.example.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.local.AutomationControlEntity
import com.example.data.local.PipelineJobEntity
import java.text.SimpleDateFormat
import java.util.*

/**
 * 60 adımlı SmartKids Otonom Üretim Standart Pipeline Aşamaları
 */
data class PipelineStageStep(
    val stepIndex: Int,
    val stageName: String,
    val stageCategory: String,
    val estimatedDurationSeconds: Int
)

val STANDARD_60_PIPELINE_STEPS: List<PipelineStageStep> = listOf(
    // 1-10: Müfredat ve DNA Keşfi (10 Adım)
    PipelineStageStep(1, "Konu ve Müfredat Analizi", "Pedagoji", 2),
    PipelineStageStep(2, "Bilişsel Seviye Doğrulama (2-4 Yaş)", "Pedagoji", 2),
    PipelineStageStep(3, "Bölüm DNA Şablon Seçimi", "Mimari", 2),
    PipelineStageStep(4, "Öğrenim Hedefleri Kilidi", "Pedagoji", 2),
    PipelineStageStep(5, "Renk Spektrumu Tanımlama (5 Renk)", "Tasarım", 2),
    PipelineStageStep(6, "Tekrarlı Telaffuz Kalıbı Oluşturma", "Fonetik", 2),
    PipelineStageStep(7, "Bilişsel Duraklama Süresi (2.0s)", "Pedagoji", 2),
    PipelineStageStep(8, "Karakter ve Sahne Dizilimi", "Kurgu", 2),
    PipelineStageStep(9, "İnteraktif Çağrı ve Tepki Planı", "Etkileşim", 2),
    PipelineStageStep(10, "Bölüm DNA JSON Kaydı & Doğrulama", "Veri", 2),

    // 11-20: Script ve Dil Yerelleştirme (10 Adım)
    PipelineStageStep(11, "Ana İngilizce (EN) Senaryo Taslağı", "Senaryo", 3),
    PipelineStageStep(12, "Leksikal Sadeleştirme ve Kelime Havuzu", "Dil", 2),
    PipelineStageStep(13, "EN Çok Dilli Yerelleştirme Matrisi", "Yerelleştirme", 3),
    PipelineStageStep(14, "Sahne 1 Kırmızı (Red) Diyalog Kilidi", "Senaryo", 2),
    PipelineStageStep(15, "Sahne 2 Mavi (Blue) Diyalog Kilidi", "Senaryo", 2),
    PipelineStageStep(16, "Sahne 3 Sarı (Yellow) Diyalog Kilidi", "Senaryo", 2),
    PipelineStageStep(17, "Sahne 4 Yeşil (Green) Diyalog Kilidi", "Senaryo", 2),
    PipelineStageStep(18, "Sahne 5 Mor (Purple) Diyalog Kilidi", "Senaryo", 2),
    PipelineStageStep(19, "Linguistik Güvenlik ve Uygunluk Taraması", "Kalite", 2),
    PipelineStageStep(20, "Son Metin Master Onayı", "Onay", 2),

    // 21-30: Piper Nöral TTS Sentezi (10 Adım)
    PipelineStageStep(21, "Piper ONNX Modeli Belleğe Yükleme", "TTS", 4),
    PipelineStageStep(22, "CC-BY-4.0 Ticari Ses Lisans Doğrulama", "Hukuk", 2),
    PipelineStageStep(23, "Sahne 1 Fonetik Ses Sentezi (Red)", "TTS", 4),
    PipelineStageStep(24, "Sahne 2 Fonetik Ses Sentezi (Blue)", "TTS", 4),
    PipelineStageStep(25, "Sahne 3 Fonetik Ses Sentezi (Yellow)", "TTS", 4),
    PipelineStageStep(26, "Sahne 4 Fonetik Ses Sentezi (Green)", "TTS", 4),
    PipelineStageStep(27, "Sahne 5 Fonetik Ses Sentezi (Purple)", "TTS", 4),
    PipelineStageStep(28, "2.0s Bilişsel Sessizlik Enjeksiyonu", "Ses Miksi", 3),
    PipelineStageStep(29, "EBU R128 (-16 LUFS) Ses Normalizasyonu", "Ses Miksi", 4),
    PipelineStageStep(30, "Master WAV Dosya Bütünlük Doğrulaması", "Ses QA", 3),

    // 31-40: Görsel Varlık & FFmpeg 1080p60 Render (10 Adım)
    PipelineStageStep(31, "1080p Sahne Katmanları Hazırlığı", "Görsel", 3),
    PipelineStageStep(32, "Çocuk Odaklı Renk Paleti Doğrulama", "Tasarım", 2),
    PipelineStageStep(33, "Sahne 1 1080p60 Video Klip Render", "Render", 8),
    PipelineStageStep(34, "Sahne 2 1080p60 Video Klip Render", "Render", 7),
    PipelineStageStep(35, "Sahne 3 1080p60 Video Klip Render", "Render", 7),
    PipelineStageStep(36, "Sahne 4 1080p60 Video Klip Render", "Render", 7),
    PipelineStageStep(37, "Sahne 5 1080p60 Video Klip Render", "Render", 8),
    PipelineStageStep(38, "FFmpeg Concat Video Birleştirme", "Render", 6),
    PipelineStageStep(39, "Master Audio ve Video Akış Senkronizasyonu", "Render", 6),
    PipelineStageStep(40, "Nihai 1080p60 MP4 Kodlama (H.264/AAC)", "Render", 9),

    // 41-50: Kalite ve Denetim Kapıları (10 Adım)
    PipelineStageStep(41, "ffprobe Teknik Video Analizi (1920x1080, 60fps)", "Teknik QA", 3),
    PipelineStageStep(42, "ffprobe Ses Akışı Denetimi (44.1kHz AAC)", "Teknik QA", 2),
    PipelineStageStep(43, "Süre Uygunluk Denetimi (45-90 Saniye)", "Standart QA", 2),
    PipelineStageStep(44, "Renk Uzayı ve Format Doğrulama (yuv420p)", "Teknik QA", 2),
    PipelineStageStep(45, "İşitsel & Görsel Pedagojik Uyum Testi", "Pedagoji QA", 3),
    PipelineStageStep(46, "0 TL Maliyet Doğrulama Denetimi", "Maliyet QA", 2),
    PipelineStageStep(47, "Otomasyon Günlük Log Oluşturma", "Loglama", 2),
    PipelineStageStep(48, "Yerel Sandbox Doğrulama ve Onay", "Onay", 2),
    PipelineStageStep(49, "Kapak Resmi (Thumbnail) Metadata Hazırlığı", "Metadata", 3),
    PipelineStageStep(50, "SEO, Başlık ve Etiket Paketleme", "SEO", 3),

    // 51-60: YouTube Yükleme, İşleme ve Yayın (10 Adım)
    PipelineStageStep(51, "YouTube OAuth Kimlik Doğrulama", "API", 4),
    PipelineStageStep(52, "Çocuklara Özel (Made for Kids) Bayrak Kilidi", "Uyumluluk", 2),
    PipelineStageStep(53, "Gizli (Private) Güvenlik Modu Kontrolü", "Güvenlik", 2),
    PipelineStageStep(54, "YouTube Resumable Video Yükleme Başlatma", "Yükleme", 12),
    PipelineStageStep(55, "Video Chunk Veri İletimi", "Yükleme", 15),
    PipelineStageStep(56, "YouTube Video ID Alınması", "API", 3),
    PipelineStageStep(57, "YouTube Sunucu Tarafı Video İşleme Takibi", "İşleme", 18),
    PipelineStageStep(58, "ProcessingStatus: Succeeded Onayı", "API", 5),
    PipelineStageStep(59, "Supabase youtube_publications Kaydı", "Veritabanı", 3),
    PipelineStageStep(60, "Yayın Döngüsü Tamamlandı & Disk Temizliği", "Tamamlandı", 2)
)

/**
 * Mevcut işin durumuna ve aşamasına göre kaçıncı adımda olduğumuzu hesaplar (1..60).
 */
fun calculatePipelineProgress(
    isEnabled: Boolean,
    activeJob: PipelineJobEntity?
): Triple<Int, PipelineStageStep, String> {
    if (activeJob == null) {
        return if (isEnabled) {
            Triple(0, PipelineStageStep(0, "Fabrika Aktif (Bulut Görevi Bekleniyor)", "Hazır / Beklemede", 0), "Görev Bekleniyor")
        } else {
            Triple(0, PipelineStageStep(0, "Fabrika Beklemede (PAUSED)", "Duraklatıldı", 0), "Durduruldu")
        }
    }

    val stepIndex = when (activeJob.status) {
        "PLANNED" -> 5
        "SCRIPTED" -> 15
        "LOCALIZED" -> 20
        "TTS_READY" -> 30
        "RENDERED" -> 40
        "QA_PASSED" -> 50
        "UPLOADING" -> 54
        "UPLOADED" -> 56
        "PROCESSING" -> 58
        "PROCESSED", "PUBLISHED", "COMPLETED", "PROCESSED_PRIVATE" -> 60
        "QA_FAILED", "QUARANTINED" -> 46
        else -> 5
    }

    val currentStep = STANDARD_60_PIPELINE_STEPS.getOrElse(stepIndex - 1) { STANDARD_60_PIPELINE_STEPS.last() }

    // Kalan adımların tahmini süresini hesapla
    val remainingSteps = STANDARD_60_PIPELINE_STEPS.filter { it.stepIndex > stepIndex }
    val remainingSeconds = remainingSteps.sumOf { it.estimatedDurationSeconds }
    val etaString = when {
        stepIndex >= 60 -> "Yayınlandı"
        remainingSeconds <= 30 -> "< 30 saniye"
        remainingSeconds < 60 -> "~${remainingSeconds} saniye"
        else -> "~${(remainingSeconds + 59) / 60} dakika"
    }

    return Triple(stepIndex, currentStep, etaString)
}

/**
 * Ana Kontrol & Canlı Üretim İlerleme Bileşeni (Tamamen Türkçe)
 */
@Composable
fun AutomationDashboardCard(
    automationControl: AutomationControlEntity?,
    activeJob: PipelineJobEntity? = null,
    onToggleEnabled: (Boolean) -> Unit,
    onRunDiagnostics: (() -> Unit)? = null,
    isDiagnosing: Boolean = false,
    diagnosticsResult: com.example.data.remote.FullDiagnosticsResult? = null,
    modifier: Modifier = Modifier
) {
    val isEnabled = automationControl?.enabled ?: false
    val statusColor by animateColorAsState(
        targetValue = if (isEnabled) Color(0xFF1B5E20) else Color(0xFFB71C1C),
        label = "statusColor"
    )
    val containerBgColor = if (isEnabled) Color(0xFFE8F5E9) else Color(0xFFFFEBEE)

    val (currentStepIndex, currentStage, etaTime) = remember(isEnabled, activeJob?.status) {
        calculatePipelineProgress(isEnabled, activeJob)
    }

    val progressFraction = if (isEnabled) (currentStepIndex / 60f).coerceIn(0f, 1f) else 0f

    // Nabız / Çalışma animasyonu
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val pulseAlpha by infiniteTransition.animateFloat(
        initialValue = 0.5f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(800, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulseAlpha"
    )

    Card(
        modifier = modifier
            .fillMaxWidth()
            .graphicsLayer {
                // Stabilize hardware-accelerated composition layer to eliminate EGL dataspace warnings
            }
            .testTag("automation_dashboard_card"),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = containerBgColor),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // 1. Üst Durum Çubuğu: ACTIVE/PAUSED ve Geçiş Anahtarı
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Surface(
                    shape = RoundedCornerShape(12.dp),
                    color = if (isEnabled) Color(0xFFC8E6C9) else Color(0xFFFFCDD2)
                ) {
                    Row(
                        modifier = Modifier
                            .padding(horizontal = 12.dp, vertical = 6.dp)
                            .testTag("dashboard_status_badge"),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(12.dp)
                                .clip(CircleShape)
                                .background(
                                    if (isEnabled) Color(0xFF2E7D32).copy(alpha = pulseAlpha)
                                    else Color(0xFFC62828)
                                )
                        )
                        Text(
                            text = if (isEnabled) "DURUM: AKTİF (ACTIVE)" else "DURUM: DURAKLATILDI (PAUSED)",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = statusColor,
                            modifier = Modifier.testTag("dashboard_status_text")
                        )
                    }
                }

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text(
                        text = if (isEnabled) "AÇIK" else "KAPALI",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = if (isEnabled) Color(0xFF2E7D32) else Color(0xFFC62828)
                    )
                    Switch(
                        checked = isEnabled,
                        onCheckedChange = { onToggleEnabled(it) },
                        modifier = Modifier.testTag("dashboard_toggle_switch")
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            Text(
                text = "SMARTKIDS BULUT FABRİKASI",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Black,
                letterSpacing = 0.5.sp
            )

            Text(
                text = "Supabase 'automation_control' Tablosu Doğrudan Bağlantısı",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(14.dp))

            // 2. CANLI AŞAMA VE İLERLEME GÖSTERGE KARTI (YENİ İSTEK)
            Surface(
                shape = RoundedCornerShape(16.dp),
                color = MaterialTheme.colorScheme.surface,
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f), RoundedCornerShape(16.dp))
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp)
                ) {
                    // Kaçıncı adımda olduğumuzu gösteren sayaç (Örn: 33/60)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.LinearScale,
                                contentDescription = null,
                                tint = if (isEnabled) MaterialTheme.colorScheme.primary else Color.Gray,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "Üretim İlerlemesi:",
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.SemiBold
                            )
                        }

                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = if (isEnabled) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant
                        ) {
                            Text(
                                text = if (isEnabled) "$currentStepIndex / 60 Adım" else "0 / 60 Adım",
                                style = MaterialTheme.typography.labelLarge,
                                fontWeight = FontWeight.Black,
                                color = if (isEnabled) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.outline,
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    // İlerleme Çubuğu (LinearProgressIndicator)
                    LinearProgressIndicator(
                        progress = { progressFraction },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(8.dp)
                            .clip(RoundedCornerShape(4.dp)),
                        color = if (isEnabled) Color(0xFF2E7D32) else Color.Gray,
                        trackColor = MaterialTheme.colorScheme.surfaceVariant
                    )

                    Spacer(modifier = Modifier.height(10.dp))

                    // Şuan hangi aşamada olduğumuzu gösteren açıklama yazısı
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.PlayArrow,
                            contentDescription = null,
                            tint = if (isEnabled) Color(0xFF2E7D32) else Color.Gray,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = if (isEnabled) "Mevcut Aşama: ${currentStage.stageName}" else "Mevcut Aşama: Üretim Duraklatıldı (Standby)",
                            style = MaterialTheme.typography.bodySmall,
                            fontWeight = FontWeight.Bold,
                            color = if (isEnabled) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.outline
                        )
                    }

                    Spacer(modifier = Modifier.height(6.dp))

                    // Tahmini Yayınlanma Süresi ve Kategori
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.Schedule,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = "Tahmini Yayın Süresi: ",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(
                                text = if (isEnabled) etaTime else "Beklemede",
                                style = MaterialTheme.typography.bodySmall,
                                fontWeight = FontWeight.ExtraBold,
                                color = if (isEnabled) Color(0xFF1565C0) else Color.Gray
                            )
                        }

                        AssistChip(
                            onClick = {},
                            label = {
                                Text(
                                    text = if (isEnabled) currentStage.stageCategory else "Kapalı",
                                    style = MaterialTheme.typography.labelSmall
                                )
                            },
                            modifier = Modifier.height(26.dp)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // 3. Son Heartbeat (Nabız) ve Çalışma Bilgisi
            val timeFormat = remember { SimpleDateFormat("HH:mm:ss", Locale.getDefault()) }
            val fullFormat = remember { SimpleDateFormat("dd.MM.yyyy HH:mm:ss", Locale.getDefault()) }
            val heartbeatMillis = automationControl?.lastHeartbeat ?: 0L
            val lastHeartbeatDisplay = remember(heartbeatMillis) {
                if (heartbeatMillis > 0L) {
                    val diffSeconds = (System.currentTimeMillis() - heartbeatMillis) / 1000
                    when {
                        diffSeconds < 60 -> "Az önce (${timeFormat.format(Date(heartbeatMillis))})"
                        diffSeconds < 3600 -> "${diffSeconds / 60} dk önce (${timeFormat.format(Date(heartbeatMillis))})"
                        else -> fullFormat.format(Date(heartbeatMillis))
                    }
                } else {
                    "Bulut runner sinyali bekleniyor..."
                }
            }

            Surface(
                shape = RoundedCornerShape(10.dp),
                color = MaterialTheme.colorScheme.surface.copy(alpha = 0.8f),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier
                        .padding(horizontal = 12.dp, vertical = 8.dp)
                        .testTag("dashboard_heartbeat_row"),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Favorite,
                        contentDescription = "Sistem Nabzı",
                        tint = if (isEnabled) Color(0xFF2E7D32) else Color(0xFF757575),
                        modifier = Modifier.size(16.dp)
                    )
                    Text(
                        text = "Son Sistem Nabzı (Heartbeat): $lastHeartbeatDisplay",
                        style = MaterialTheme.typography.bodySmall,
                        fontWeight = FontWeight.Medium,
                        color = MaterialTheme.colorScheme.onSurface,
                        modifier = Modifier.testTag("dashboard_heartbeat_text")
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // 4. Ana Geçiş Düğmesi (START FACTORY / STOP FACTORY - TÜRKÇE VE NET)
            Button(
                onClick = { onToggleEnabled(!isEnabled) },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(62.dp)
                    .testTag("dashboard_master_toggle_button"),
                shape = RoundedCornerShape(16.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isEnabled) Color(0xFFC62828) else Color(0xFF2E7D32),
                    contentColor = Color.White
                ),
                elevation = ButtonDefaults.buttonElevation(defaultElevation = 4.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Center
                ) {
                    Icon(
                        imageVector = if (isEnabled) Icons.Default.StopCircle else Icons.Default.PlayCircle,
                        contentDescription = if (isEnabled) "Üretimi Durdur" else "Üretimi Başlat",
                        modifier = Modifier.size(30.dp)
                    )
                    Spacer(modifier = Modifier.width(10.dp))
                    Column(horizontalAlignment = Alignment.Start) {
                        Text(
                            text = if (isEnabled) "ÜRETİMİ DURDUR (STOP FACTORY)" else "ÜRETİMİ BAŞLAT (START FACTORY)",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Black,
                            letterSpacing = 0.5.sp
                        )
                        Text(
                            text = if (isEnabled)
                                "Supabase automation_control.enabled = FALSE yap"
                            else
                                "Supabase automation_control.enabled = TRUE yap",
                            style = MaterialTheme.typography.labelSmall,
                            color = Color.White.copy(alpha = 0.9f)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // 5. BAĞLANTI DURUM ÇUBUĞU (Supabase • GitHub • YouTube -> Bağlı / Hatalı)
            Surface(
                shape = RoundedCornerShape(14.dp),
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
                modifier = Modifier
                    .fillMaxWidth()
                    .testTag("connectivity_status_bar")
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 10.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceEvenly,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    val supabaseRes = diagnosticsResult?.results?.find { it.serviceName.contains("Supabase", ignoreCase = true) }
                    val githubRes = diagnosticsResult?.results?.find { it.serviceName.contains("GitHub", ignoreCase = true) }
                    val youtubeRes = diagnosticsResult?.results?.find { it.serviceName.contains("YouTube", ignoreCase = true) }

                    ServiceStatusChip(
                        name = "Supabase",
                        status = supabaseRes?.status,
                        isChecking = isDiagnosing
                    )
                    VerticalDivider(modifier = Modifier.height(20.dp), thickness = 1.dp, color = MaterialTheme.colorScheme.outlineVariant)
                    ServiceStatusChip(
                        name = "GitHub",
                        status = githubRes?.status,
                        isChecking = isDiagnosing
                    )
                    VerticalDivider(modifier = Modifier.height(20.dp), thickness = 1.dp, color = MaterialTheme.colorScheme.outlineVariant)
                    ServiceStatusChip(
                        name = "YouTube",
                        status = youtubeRes?.status,
                        isChecking = isDiagnosing
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // 6. BAĞLANTI TESTİ BUTONU (Eşzamanlı Supabase, GitHub ve YouTube Kontrolü)
            if (onRunDiagnostics != null) {
                OutlinedButton(
                    onClick = onRunDiagnostics,
                    enabled = !isDiagnosing,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(50.dp)
                        .testTag("btn_run_diagnostics"),
                    shape = RoundedCornerShape(14.dp),
                    colors = ButtonDefaults.outlinedButtonColors(
                        contentColor = MaterialTheme.colorScheme.primary
                    )
                ) {
                    if (isDiagnosing) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            strokeWidth = 2.dp,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Bağlantılar Eşzamanlı Test Ediliyor...",
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Bold
                        )
                    } else {
                        Icon(
                            imageVector = Icons.Default.NetworkCheck,
                            contentDescription = "Bağlantı Testi",
                            modifier = Modifier.size(22.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "BAĞLANTI TESTİ (Eşzamanlı Uç Nokta Kontrolü)",
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = if (isEnabled)
                    "Fabrika şu an AKTİF: GitHub Actions ARM64 bulut ortamında bağımsız üretim sürüyor."
                else
                    "Fabrika DURDURULDU: Devam eden işlem güvenle tamamlanır, yeni bölüm başlatılmaz.",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.outline,
                textAlign = TextAlign.Center
            )
        }
    }
}

@Composable
private fun ServiceStatusChip(
    name: String,
    status: com.example.data.remote.ServiceStatus?,
    isChecking: Boolean
) {
    val (label, dotColor, textColor) = when {
        isChecking -> Triple("Test...", Color(0xFFFBC02D), Color(0xFFF57F17))
        status == com.example.data.remote.ServiceStatus.SUCCESS -> Triple("Bağlı", Color(0xFF2E7D32), Color(0xFF1B5E20))
        status == com.example.data.remote.ServiceStatus.WARNING -> Triple("Uyarı", Color(0xFFF57C00), Color(0xFFE65100))
        status == com.example.data.remote.ServiceStatus.FAILED -> Triple("Hatalı", Color(0xFFC62828), Color(0xFFB71C1C))
        else -> Triple("Hazır", Color(0xFF757575), Color(0xFF424242))
    }

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(5.dp),
        modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)
    ) {
        Box(
            modifier = Modifier
                .size(9.dp)
                .clip(CircleShape)
                .background(dotColor)
        )
        Text(
            text = "$name: $label",
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Bold,
            color = textColor
        )
    }
}

