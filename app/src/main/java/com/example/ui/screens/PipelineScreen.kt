package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.local.EpisodeDnaEntity
import com.example.data.local.PipelineJobEntity
import com.example.ui.components.CodeViewBlock
import com.example.ui.components.GatingBlockerBanner
import com.example.ui.components.StatusBadge
import com.example.ui.theme.*

@Composable
fun PipelineScreen(
    jobs: List<PipelineJobEntity>,
    episodes: List<EpisodeDnaEntity>,
    unapprovedVoiceCount: Int,
    onStepJob: (PipelineJobEntity) -> Unit,
    onCreateJob: (EpisodeDnaEntity, String) -> Unit,
    modifier: Modifier = Modifier
) {
    var showCreateDialog by remember { mutableStateOf(false) }
    var selectedEpisode by remember { mutableStateOf<EpisodeDnaEntity?>(null) }
    var selectedLang by remember { mutableStateOf("EN") }

    val languages = listOf("EN", "ES", "DE", "FR", "PT", "AR", "HI", "ZH", "JA", "TR")

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        contentPadding = PaddingValues(top = 12.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        if (unapprovedVoiceCount > 0) {
            item {
                GatingBlockerBanner(unapprovedCount = unapprovedVoiceCount)
            }
        }

        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "Otonom İş Akışı",
                        style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.onBackground
                    )
                    Text(
                        text = "Deterministik Render • YouTube Durum Makinesi • Sıfır Disk Sızıntısı",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Button(
                    onClick = {
                        selectedEpisode = episodes.firstOrNull()
                        showCreateDialog = true
                    },
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = IndigoPrimary)
                ) {
                    Icon(imageVector = Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(text = "Yeni Görev", fontSize = 12.sp)
                }
            }
        }

        // State Machine Flow Banner
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text(
                        text = "Otonom Yükleme ve Güvenli Silme Durum Makinesi",
                        fontWeight = FontWeight.Bold,
                        fontSize = 13.sp,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "RENDERED ➔ UPLOADING ➔ UPLOADED ➔ PROCESSING ➔ PROCESSED ➔ PUBLISHED ➔ DELETE_LOCAL_FILE",
                        fontFamily = FontFamily.Monospace,
                        fontSize = 11.sp,
                        color = SkyCyanLight,
                        lineHeight = 16.sp
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "🔒 Depolama İlkesi: MP4 dosyası yükleme biter bitmez silinmez. YouTube arka plan işleme başarısı ('succeeded') teyidi ve veritabanı onayından sonra yerel diskten silinir.",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        // Active Jobs
        item {
            Text(
                text = "İş Akışı Görevleri (${jobs.size})",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onBackground
            )
        }

        items(jobs, key = { it.jobId }) { job ->
            JobCard(
                job = job,
                onStep = { onStepJob(job) }
            )
        }

        // Deterministic render explanation
        item {
            CodeViewBlock(
                title = "Deterministik SHA-256 Seed Formülü",
                code = """// Python / Çalışan Tekrarlanabilirlik Formülü:
// seed = SHA256(episode_id + language + template_version)
// rng = random.Random(seed)
//
// Garanti Edilen: İlk render == Tekrar render == %100 aynı video/renk/ses çıktısı.
// Piksel gürültüsü ve yapay zeka sapması sıfırdır."""
            )
        }
    }

    if (showCreateDialog) {
        AlertDialog(
            onDismissRequest = { showCreateDialog = false },
            title = { Text("Yeni İş Akışı Başlat") },
            text = {
                Column {
                    Text("Hedef Dili Seçin (10 YouTube Kanalından biri):", fontSize = 13.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        languages.take(5).forEach { lang ->
                            FilterChip(
                                selected = selectedLang == lang,
                                onClick = { selectedLang = lang },
                                label = { Text(lang, fontSize = 11.sp) }
                            )
                        }
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        languages.takeLast(5).forEach { lang ->
                            FilterChip(
                                selected = selectedLang == lang,
                                onClick = { selectedLang = lang },
                                label = { Text(lang, fontSize = 11.sp) }
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))
                    Text("Bölüm DNA: ${selectedEpisode?.title ?: "Bölüm Seçin"}", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val ep = selectedEpisode ?: episodes.firstOrNull()
                        if (ep != null) {
                            onCreateJob(ep, selectedLang)
                            showCreateDialog = false
                        }
                    }
                ) {
                    Text("Başlat")
                }
            },
            dismissButton = {
                TextButton(onClick = { showCreateDialog = false }) {
                    Text("İptal")
                }
            }
        )
    }
}

@Composable
fun JobCard(
    job: PipelineJobEntity,
    onStep: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        border = androidx.compose.foundation.BorderStroke(
            1.dp,
            when (job.status) {
                "PUBLISHED", "DELETE_LOCAL_FILE", "ARCHIVED_ZERO_BLOAT" -> EmeraldPass.copy(alpha = 0.5f)
                "QA_FAILED", "QUARANTINED" -> CrimsonBlock.copy(alpha = 0.5f)
                else -> SkyCyanLight.copy(alpha = 0.5f)
            }
        ),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Surface(
                        shape = RoundedCornerShape(4.dp),
                        color = IndigoPrimary.copy(alpha = 0.2f),
                        border = androidx.compose.foundation.BorderStroke(1.dp, IndigoLight)
                    ) {
                        Text(
                            text = job.languageCode,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = IndigoLight,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = job.jobId,
                        fontFamily = FontFamily.Monospace,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }

                StatusBadge(
                    text = job.status,
                    isSuccess = job.status in listOf("PUBLISHED", "PROCESSED", "DELETE_LOCAL_FILE", "ARCHIVED_ZERO_BLOAT"),
                    isWarning = job.status in listOf("RENDERED", "UPLOADING", "UPLOADED", "PROCESSING")
                )
            }

            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = job.title,
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium,
                color = MaterialTheme.colorScheme.onSurface
            )

            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Seed: ${job.deterministicSeed.take(20)}...",
                fontFamily = FontFamily.Monospace,
                fontSize = 10.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(6.dp))
            Surface(
                color = MaterialTheme.colorScheme.background.copy(alpha = 0.6f),
                shape = RoundedCornerShape(6.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = job.logMessage,
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(8.dp),
                    lineHeight = 15.sp
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = if (job.localFileDeleted) "✅ Yerel Dosya Silindi (0 MB Sızıntı)" else "⏳ Yerel Dosya Korunuyor (Teyit Bekleniyor)",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                    color = if (job.localFileDeleted) EmeraldPass else AmberGlow
                )

                OutlinedButton(
                    onClick = onStep,
                    shape = RoundedCornerShape(8.dp),
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 6.dp)
                ) {
                    Icon(imageVector = Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(14.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(text = "Durumu İlerlet", fontSize = 11.sp)
                }
            }
        }
    }
}
