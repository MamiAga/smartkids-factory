package com.example.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
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
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.local.AutomationControlEntity
import com.example.data.local.PipelineJobEntity
import com.example.data.local.SystemEventEntity
import com.example.ui.components.AutomationDashboardCard
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
    diagnosticsResult: com.example.data.remote.FullDiagnosticsResult? = null
) {
    val isEnabled = automationControl?.enabled ?: false
    val dailyEpisodes = automationControl?.dailyMasterEpisodes ?: 1
    val activeLangsJson = automationControl?.activeLanguagesJson ?: "[\"EN\"]"

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

    val producedCount = jobs.count { it.status == "PUBLISHED" || it.status == "COMPLETED" || it.status == "PROCESSED" }
    val uploadingCount = jobs.count { it.status == "UPLOADING" || it.status == "UPLOADED" || it.status == "PROCESSING" }
    val pendingCount = jobs.count { it.status == "PLANNED" || it.status == "SCRIPTED" || it.status == "TTS_READY" || it.status == "RENDERED" }
    val failedCount = jobs.count { it.status == "QA_FAILED" || it.status == "QUARANTINED" }

    val statusColor by animateColorAsState(
        targetValue = if (isEnabled) Color(0xFF1B5E20) else Color(0xFFB71C1C),
        label = "statusColor"
    )

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .testTag("control_center_screen"),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // 1. HERO MASTER CONTROL CARD (Supabase automation_control connected component)
        item {
            val activeJob = jobs.firstOrNull { 
                it.status != "PUBLISHED" && it.status != "COMPLETED" && it.status != "PROCESSED"
            } ?: jobs.firstOrNull()
            AutomationDashboardCard(
                automationControl = automationControl,
                activeJob = activeJob,
                onToggleEnabled = { onToggleFactory(it) },
                onRunDiagnostics = onRunDiagnostics,
                isDiagnosing = isDiagnosing,
                diagnosticsResult = diagnosticsResult
            )
        }

        // 2. DAILY TARGET & CALCULATION CARD
        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
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

                    Spacer(modifier = Modifier.height(16.dp))

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
                                fontWeight = FontWeight.Bold
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

        // 3. TODAY'S PRODUCTION METRICS GRID
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    text = "BUGÜNKÜ DURUM & KUYRUK",
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
                        title = "Hatalı/Karantina",
                        count = failedCount,
                        color = Color(0xFFC62828),
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }

        // 4. LANGUAGE MATRIX SELECTION
        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
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

        // 5. CLOUD INFRASTRUCTURE & HEARTBEAT STATUS
        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
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

        // 6. OPERATIONAL SYSTEM LOGS
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
                    modifier = Modifier.fillMaxWidth().border(1.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(12.dp))
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
}

@Composable
fun MetricBox(
    title: String,
    count: Int,
    color: Color,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier,
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
