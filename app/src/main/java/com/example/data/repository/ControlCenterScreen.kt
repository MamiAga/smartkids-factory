package com.example.ui.screens

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.local.AutomationControlEntity
import com.example.data.local.PipelineJobEntity
import com.example.data.local.SystemEventEntity
import com.example.data.remote.FullDiagnosticsResult
import com.example.ui.components.*
import com.example.ui.theme.*
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun ControlCenterScreen(
    automationControl: AutomationControlEntity?,
    jobs: List<PipelineJobEntity>,
    events: List<SystemEventEntity>,
    onToggleFactory: (Boolean) -> Unit,
    onUpdateDailyTarget: (Int) -> Unit,
    onToggleLanguage: (String) -> Unit,
    onRunDiagnostics: (() -> Unit)? = null,
    isDiagnosing: Boolean = false,
    diagnosticsResult: FullDiagnosticsResult? = null,
    onSyncCloud: (() -> Unit)? = null,
    isSyncing: Boolean = false,
    onQuickDispatch: ((String, String) -> Unit)? = null,
    onStepJob: ((PipelineJobEntity) -> Unit)? = null
) {
    val context = LocalContext.current
    val isEnabled = automationControl?.enabled ?: false
    val dailyEpisodes = automationControl?.dailyMasterEpisodes ?: 1
    val activeLangsJson = automationControl?.activeLanguagesJson ?: "[\"EN\"]"

    var showQuickDispatchDialog by remember { mutableStateOf(false) }
    var selectedDispatchLang by remember { mutableStateOf("EN") }
    var selectedDispatchEpisode by remember { mutableStateOf("EP-COLORS-5-V1") }

    val activeLanguages = remember(activeLangsJson) {
        val list = mutableListOf<String>()
        val cleaned = activeLangsJson.trim().removeSurrounding("[", "]")
        if (cleaned.isNotBlank()) {
            cleaned.split(",").map { it.trim().removeSurrounding("\"") }.filter { it.isNotEmpty() }.forEach { list.add(it) }
        }
        if (list.isEmpty()) list.add("EN")
        list
    }

    val expectedVideos = dailyEpisodes * activeLanguages.size

    val producedCount = jobs.count { it.status in CloudJobStates.PRODUCED }
    val uploadingCount = jobs.count { it.status in listOf("UPLOADING", "UPLOADED", "PROCESSING") && CloudJobStates.isRunning(it) }
    val pendingCount = jobs.count { it.status !in CloudJobStates.TERMINAL && it.status !in listOf("UPLOADING", "UPLOADED", "PROCESSING") && CloudJobStates.isRunning(it) }
    val failedCount = jobs.count { it.status in CloudJobStates.FAILED }

    // Sadece bulutta gerçekten devam eden (ve son 2 saatte güncellenmiş) iş aktif iştir
    val activeJob = jobs.firstOrNull { CloudJobStates.isRunning(it) }
    val displayJob = activeJob ?: jobs.firstOrNull()

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .testTag("control_center_screen"),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // 1. QUICK ACTION COMMAND DECK (Mobil Hızlı Aksiyon Çubuğu)
        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .graphicsLayer { },
                shape = RoundedCornerShape(18.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.7f)),
                border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "HIZLI BULUT KUMANDASI",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Black,
                            color = MaterialTheme.colorScheme.primary,
                            letterSpacing = 0.5.sp
                        )
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(8.dp)
                                    .clip(CircleShape)
                                    .background(if (isEnabled) EmeraldPass else CrimsonBlock)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = if (isEnabled) "CANLI ÇALIŞIYOR" else "BEKLEMEDE",
                                style = MaterialTheme.typography.labelSmall,
                                fontWeight = FontWeight.Bold,
                                color = if (isEnabled) EmeraldPass else CrimsonBlock
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        // 1. Yeni Üretim Tetikle
                        FilledTonalButton(
                            onClick = { showQuickDispatchDialog = true },
                            modifier = Modifier.weight(1f),
                            shape = RoundedCornerShape(12.dp),
                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 10.dp)
                        ) {
                            Icon(Icons.Default.RocketLaunch, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Üretim Başlat", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }

                        // 2. Supabase Senkronize Et
                        if (onSyncCloud != null) {
                            Button(
                                onClick = onSyncCloud,
                                enabled = !isSyncing,
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(12.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = IndigoPrimary),
                                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 10.dp)
                            ) {
                                if (isSyncing) {
                                    CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp, color = Color.White)
                                } else {
                                    Icon(Icons.Default.Sync, contentDescription = null, modifier = Modifier.size(16.dp))
                                }
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(if (isSyncing) "Çekiliyor..." else "Bulut Senk.", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }
        }

        // 2. HERO MASTER AUTOMATION DASHBOARD CARD (60-Adım İlerleme ve Ana Şalter)
        item {
            AutomationDashboardCard(
                automationControl = automationControl,
                activeJob = activeJob,
                onToggleEnabled = { onToggleFactory(it) },
                onRunDiagnostics = onRunDiagnostics,
                isDiagnosing = isDiagnosing,
                diagnosticsResult = diagnosticsResult
            )
        }

        // 3. CANLI İŞ VEYA SON ÜRETİM TAKİP PANELİ
        if (displayJob != null) {
            item {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .graphicsLayer { }
                        .testTag("active_job_cockpit_card"),
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    border = androidx.compose.foundation.BorderStroke(1.5.dp, if (activeJob != null) MaterialTheme.colorScheme.primary.copy(alpha = 0.6f) else MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f)),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(modifier = Modifier.padding(18.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Surface(
                                    shape = RoundedCornerShape(6.dp),
                                    color = if (activeJob != null) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant
                                ) {
                                    Text(
                                        text = displayJob.languageCode,
                                        style = MaterialTheme.typography.labelMedium,
                                        fontWeight = FontWeight.Black,
                                        color = if (activeJob != null) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onSurfaceVariant,
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                    )
                                }
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = displayJob.episodeId,
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.Bold
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                if (activeJob == null) {
                                    Text(
                                        text = "(Son Üretim)",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.outline
                                    )
                                }
                            }

                            StatusBadge(
                                text = displayJob.status,
                                isSuccess = displayJob.status in listOf("PUBLISHED", "PROCESSED", "PROCESSED_PRIVATE", "COMPLETED"),
                                isWarning = displayJob.status in listOf("RENDERED", "UPLOADING", "UPLOADED", "PROCESSING")
                            )
                        }

                        Spacer(modifier = Modifier.height(10.dp))

                        Text(
                            text = displayJob.title,
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.SemiBold
                        )

                        Spacer(modifier = Modifier.height(8.dp))

                        // YouTube Video ID Row
                        Surface(
                            shape = RoundedCornerShape(10.dp),
                            color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier
                                    .padding(horizontal = 12.dp, vertical = 8.dp)
                                    .clickable {
                                        if (displayJob.youtubeVideoId.isNotBlank()) {
                                            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                            clipboard.setPrimaryClip(ClipData.newPlainText("YouTube ID", displayJob.youtubeVideoId))
                                        }
                                    },
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(
                                        imageVector = Icons.Default.PlayCircle,
                                        contentDescription = null,
                                        tint = Color(0xFFFF0000),
                                        modifier = Modifier.size(18.dp)
                                    )
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text(
                                        text = if (displayJob.youtubeVideoId.isNotBlank()) "YouTube Video ID: ${displayJob.youtubeVideoId}" else "YouTube Video ID: Bekleniyor...",
                                        style = MaterialTheme.typography.bodySmall,
                                        fontFamily = FontFamily.Monospace,
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                                if (displayJob.youtubeVideoId.isNotBlank()) {
                                    Icon(
                                        imageVector = Icons.Default.ContentCopy,
                                        contentDescription = "Kopyala",
                                        tint = MaterialTheme.colorScheme.outline,
                                        modifier = Modifier.size(16.dp)
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        // Teknik Özellikler Satırı
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = "1080p60 H.264 • -16 LUFS AAC",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.outline
                            )
                            Text(
                                text = "Maliyet: 0.00 USD (0 TL)",
                                style = MaterialTheme.typography.labelSmall,
                                fontWeight = FontWeight.Bold,
                                color = EmeraldPass
                            )
                        }

                        if (onStepJob != null && activeJob != null) {
                            Spacer(modifier = Modifier.height(10.dp))
                            OutlinedButton(
                                onClick = { onStepJob(activeJob) },
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(10.dp)
                            ) {
                                Icon(Icons.Default.FastForward, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                Text("Aşamayı İlerlet (${activeJob.status})", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }
        }

        // 4. TODAY'S PRODUCTION KPI METRICS GRID
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    text = "GÜNLÜK ÜRETİM & KUYRUK DURUMU",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    MetricBox(
                        title = "Tamamlanan",
                        count = producedCount,
                        color = Color(0xFF2E7D32),
                        modifier = Modifier.weight(1f)
                    )
                    MetricBox(
                        title = "Yükleniyor",
                        count = uploadingCount,
                        color = Color(0xFF1565C0),
                        modifier = Modifier.weight(1f)
                    )
                    MetricBox(
                        title = "Bekleyen",
                        count = pendingCount,
                        color = Color(0xFFF57F17),
                        modifier = Modifier.weight(1f)
                    )
                    MetricBox(
                        title = "Karantina",
                        count = failedCount,
                        color = Color(0xFFC62828),
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }

        // 5. DAILY TARGET & MULTI-LANGUAGE CAPACITY CALCULATOR
        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .graphicsLayer { }
                    .testTag("target_calculation_card"),
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "GÜNLÜK ÜRETİM HEDEFİ",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold
                        )
                        AssistChip(
                            onClick = {},
                            label = { Text("0 TL Kota Koruması") },
                            leadingIcon = { Icon(Icons.Default.Shield, contentDescription = null, modifier = Modifier.size(16.dp)) }
                        )
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column {
                            Text(
                                text = "Günlük Master Bölüm",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(
                                text = "$dailyEpisodes Bölüm / Gün",
                                style = MaterialTheme.typography.titleLarge,
                                fontWeight = FontWeight.Black
                            )
                        }

                        // Stepper buttons
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            FilledTonalIconButton(
                                onClick = { if (dailyEpisodes > 1) onUpdateDailyTarget(dailyEpisodes - 1) },
                                enabled = dailyEpisodes > 1,
                                modifier = Modifier.testTag("btn_target_decrease")
                            ) {
                                Icon(Icons.Default.Remove, contentDescription = "Azalt")
                            }
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "$dailyEpisodes",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            FilledTonalIconButton(
                                onClick = { if (dailyEpisodes < 10) onUpdateDailyTarget(dailyEpisodes + 1) },
                                enabled = dailyEpisodes < 10,
                                modifier = Modifier.testTag("btn_target_increase")
                            ) {
                                Icon(Icons.Default.Add, contentDescription = "Artır")
                            }
                        }
                    }

                    HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp))

                    // Calculation formula row
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "$dailyEpisodes master × ${activeLanguages.size} aktif dil",
                            style = MaterialTheme.typography.bodyMedium
                        )
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = MaterialTheme.colorScheme.primaryContainer
                        ) {
                            Text(
                                text = "= $expectedVideos YouTube Videosu / Gün",
                                modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                                style = MaterialTheme.typography.labelLarge,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onPrimaryContainer
                            )
                        }
                    }
                }
            }
        }

        // 6. LANGUAGE MATRIX SELECTION (EN, ES, DE, FR, PT)
        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .graphicsLayer { }
                    .testTag("language_matrix_card"),
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text(
                        text = "AKTİF ÜRETİM DİLLERİ",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Yalnızca ticari kullanım lisansı onaylanmış Piper modelleri üretimdedir.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline
                    )

                    Spacer(modifier = Modifier.height(12.dp))

                    val productionLangs = listOf(
                        "EN" to "English (US)",
                        "ES" to "Spanish",
                        "DE" to "German",
                        "FR" to "French",
                        "PT" to "Portuguese"
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        productionLangs.forEach { (code, name) ->
                            val isSelected = activeLanguages.contains(code)
                            FilterChip(
                                selected = isSelected,
                                onClick = { onToggleLanguage(code) },
                                label = { Text(code) },
                                leadingIcon = if (isSelected) {
                                    { Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(16.dp)) }
                                } else null,
                                modifier = Modifier.testTag("chip_lang_$code")
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    Text(
                        text = "Pilot Değerlendirme (Kilitli): AR, HI, ZH, JA, TR",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.outline
                    )
                }
            }
        }

        // 7. CLOUD INFRASTRUCTURE & HEARTBEAT STATUS
        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .graphicsLayer { }
                    .testTag("cloud_infra_card"),
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text(
                        text = "BULUT ALTYAPI DURUMU & HEARTBEAT",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold
                    )

                    Spacer(modifier = Modifier.height(12.dp))

                    InfraItem(title = "GitHub Actions Runner", value = "ubuntu-24.04-arm (aarch64)", ok = true)
                    InfraItem(title = "Supabase PostgreSQL", value = "PostgREST 16 Cloud DB", ok = true)
                    InfraItem(title = "Piper Neural TTS", value = "LibriTTS-R (CC-BY 4.0)", ok = true)
                    InfraItem(title = "FFmpeg Render", value = "1080p60 H.264 / AAC", ok = true)
                    InfraItem(title = "YouTube Data API v3", value = "Private Mode (Unverified Audit Safe)", ok = true)
                    InfraItem(title = "0 TL Maliyet Tavanı", value = "ALLOW_PAID_SERVICES = false", ok = true)

                    Spacer(modifier = Modifier.height(8.dp))
                    HorizontalDivider()
                    Spacer(modifier = Modifier.height(8.dp))

                    val timeFormat = remember { SimpleDateFormat("HH:mm:ss dd.MM.yyyy", Locale.getDefault()) }
                    val lastHeartbeatStr = automationControl?.lastHeartbeat?.let { timeFormat.format(Date(it)) } ?: "Bekleniyor"

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text("Son Heartbeat:", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
                        Text(lastHeartbeatStr, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text("Zamanlama:", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
                        Text("${automationControl?.scheduleTime ?: "04:00"} (${automationControl?.timezone ?: "Europe/Istanbul"})", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        // 8. OPERATIONAL SYSTEM LOGS
        item {
            Text(
                text = "SON SİSTEM VE HEARTBEAT GÜNLÜĞÜ",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        if (events.isEmpty()) {
            item {
                Text(
                    text = "Henüz sistem günlüğü kaydı yok.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline
                )
            }
        } else {
            items(events.take(6)) { event ->
                Surface(
                    shape = RoundedCornerShape(12.dp),
                    color = MaterialTheme.colorScheme.surface,
                    modifier = Modifier
                        .fillMaxWidth()
                        .graphicsLayer { }
                        .border(1.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(12.dp))
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = event.eventType,
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.Bold,
                                color = if (event.severity == "WARNING" || event.severity == "ERROR") Color(0xFFC62828) else MaterialTheme.colorScheme.primary
                            )
                            val tf = remember { SimpleDateFormat("HH:mm:ss", Locale.getDefault()) }
                            Text(
                                text = tf.format(Date(event.timestamp)),
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.outline
                            )
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = event.message,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
            }
        }
    }

    // Quick Dispatch Dialog
    if (showQuickDispatchDialog) {
        AlertDialog(
            onDismissRequest = { showQuickDispatchDialog = false },
            icon = { Icon(Icons.Default.RocketLaunch, contentDescription = null, tint = MaterialTheme.colorScheme.primary) },
            title = { Text("Bulut Üretimini Tetikle") },
            text = {
                Column {
                    Text("Bölüm DNA: EP-COLORS-5-V1 (Renkleri Öğrenelim)", fontSize = 13.sp, fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.height(10.dp))
                    Text("Hedef Dil Seçin:", fontSize = 12.sp, color = MaterialTheme.colorScheme.outline)
                    Spacer(modifier = Modifier.height(6.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        listOf("EN", "ES", "DE", "FR", "PT").forEach { lang ->
                            FilterChip(
                                selected = selectedDispatchLang == lang,
                                onClick = { selectedDispatchLang = lang },
                                label = { Text(lang, fontSize = 12.sp) }
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("Privacy: PRIVATE • Made For Kids: TRUE • 0 TL Maliyet", fontSize = 11.sp, color = EmeraldPass, fontWeight = FontWeight.Bold)
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        onQuickDispatch?.invoke(selectedDispatchEpisode, selectedDispatchLang)
                        showQuickDispatchDialog = false
                    }
                ) {
                    Text("Üretimi Başlat")
                }
            },
            dismissButton = {
                TextButton(onClick = { showQuickDispatchDialog = false }) {
                    Text("Vazgeç")
                }
            }
        )
    }
}

@Composable
fun MetricBox(
    title: String,
    count: Int,
    color: Color,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier.graphicsLayer { },
        shape = RoundedCornerShape(14.dp),
        color = MaterialTheme.colorScheme.surfaceVariant
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "$count",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Black,
                color = color
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = title,
                style = MaterialTheme.typography.labelSmall,
                textAlign = TextAlign.Center,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
fun InfraItem(
    title: String,
    value: String,
    ok: Boolean
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = if (ok) Icons.Default.CheckCircle else Icons.Default.Warning,
                contentDescription = null,
                tint = if (ok) Color(0xFF2E7D32) else Color(0xFFC62828),
                modifier = Modifier.size(16.dp)
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text(text = title, style = MaterialTheme.typography.bodySmall)
        }
        Text(
            text = value,
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onSurface
        )
    }
}
