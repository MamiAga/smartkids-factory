package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.FactCheck
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.local.VoiceLicenseEntity
import com.example.ui.components.GatingBlockerBanner
import com.example.ui.components.StatusBadge
import com.example.ui.theme.*

@Composable
fun VoiceRegistryScreen(
    voices: List<VoiceLicenseEntity>,
    unapprovedCount: Int,
    inspectedAuditRecord: String?,
    isLoading: Boolean,
    onToggleApproval: (VoiceLicenseEntity) -> Unit,
    onInspectAudit: (VoiceLicenseEntity) -> Unit,
    onDismissAuditDialog: () -> Unit,
    modifier: Modifier = Modifier
) {
    val approvedCount = voices.count { it.isApproved && it.isCommercialUseAllowed }
    val blockedCount = voices.size - approvedCount

    if (inspectedAuditRecord != null) {
        AlertDialog(
            onDismissRequest = onDismissAuditDialog,
            title = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(imageVector = Icons.Default.VerifiedUser, contentDescription = null, tint = SkyCyanLight)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Model Kartı ve Lisans Denetim Kaydı", fontSize = 15.sp, fontWeight = FontWeight.Bold)
                }
            },
            text = {
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = inspectedAuditRecord,
                        fontFamily = FontFamily.Monospace,
                        fontSize = 11.sp,
                        lineHeight = 16.sp,
                        color = MaterialTheme.colorScheme.onSurface,
                        modifier = Modifier.padding(12.dp)
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = onDismissAuditDialog) {
                    Text("Denetim Kaydını Kapat", fontWeight = FontWeight.Bold)
                }
            }
        )
    }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        contentPadding = PaddingValues(top = 12.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        // Gating Blocker Summary Banner
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = CrimsonBlock.copy(alpha = 0.15f)),
                border = androidx.compose.foundation.BorderStroke(1.dp, CrimsonBlock),
                shape = RoundedCornerShape(10.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(imageVector = Icons.Default.Gavel, contentDescription = null, tint = CrimsonBlock, modifier = Modifier.size(20.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "ÜRETİM DURUMU = HAZIR DEĞİL ($approvedCount/10 ONAYLI)",
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                            color = CrimsonBlock
                        )
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Sıfır Toleranslı Üretim Kapısı: Ticari geçerlilik 5/10 dil (EN, ES, DE, FR, PT) için doğrulanmıştır. 5 dil (HI, AR, ZH, JA, TR) kesin olarak KİLİTLİDİR. Chatterbox Multilingual V3, bu 5 kilitli dil için birleşik bir PİLOT ADAYI olarak canlı test edilmektedir.",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurface,
                        lineHeight = 16.sp
                    )
                }
            }
        }

        // Chatterbox Multilingual V3 Pilot Evaluation Card
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                border = androidx.compose.foundation.BorderStroke(1.dp, AmberAccent),
                shape = RoundedCornerShape(10.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(imageVector = Icons.Default.Science, contentDescription = null, tint = AmberAccent, modifier = Modifier.size(20.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Chatterbox Multilingual V3",
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        }
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = AmberAccent.copy(alpha = 0.2f),
                            border = androidx.compose.foundation.BorderStroke(1.dp, AmberAccent)
                        ) {
                            Text(
                                text = "PİLOT ADAYI",
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Bold,
                                color = AmberAccent,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Eksik 5 dil (AR, HI, JA, TR, ZH) için birleşik aday. 23 dil desteği, ~500M parametre, 2.14 GB safetensors model dosyası.",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        lineHeight = 16.sp
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = EmeraldPass.copy(alpha = 0.15f),
                            modifier = Modifier.weight(1f)
                        ) {
                            Column(modifier = Modifier.padding(8.dp)) {
                                Text("A. Hukuk / Lisans", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = EmeraldPass)
                                Text("MIT (Dataset: ?) ", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurface)
                            }
                        }
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = AmberAccent.copy(alpha = 0.15f),
                            modifier = Modifier.weight(1f)
                        ) {
                            Column(modifier = Modifier.padding(8.dp)) {
                                Text("B. ARM64 / CPU", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = AmberAccent)
                                Text("DOĞRULANMADI", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = AmberAccent)
                            }
                        }
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = AmberAccent.copy(alpha = 0.15f),
                            modifier = Modifier.weight(1f)
                        ) {
                            Column(modifier = Modifier.padding(8.dp)) {
                                Text("C. Kalite / QA", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = AmberAccent)
                                Text("DOĞRULANMADI", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = AmberAccent)
                            }
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Teknik Notlar: Perth filigranı çıktıda mevcuttur (hukuki muafiyet garantisi içermez). Arapça kelime başı hamza silinme riski (Issue #555) ve CPU aygıt hatası (#533) için Oracle canlı testi zorunludur. Referans ses hakları kanıtlanana kadar ses klonlama KİLİTLİDİR.",
                        fontSize = 10.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        lineHeight = 14.sp
                    )
                }
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
                        text = "10 Dilli Piper Ses Matrisi",
                        style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.onBackground
                    )
                    Text(
                        text = "Ayrıştırılmış Motor / Model / Veri Seti Hak Zinciri",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = CrimsonBlock.copy(alpha = 0.2f),
                    border = androidx.compose.foundation.BorderStroke(1.dp, CrimsonBlock)
                ) {
                    Text(
                        text = "$blockedCount KİLİTLİ / $approvedCount HAZIR",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = CrimsonBlock,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
            }
        }

        // 10 Language Cards
        items(voices, key = { it.voiceId }) { voice ->
            VoiceDetailedCard(
                voice = voice,
                isLoading = isLoading,
                onToggleApproval = { onToggleApproval(voice) },
                onInspectAudit = { onInspectAudit(voice) }
            )
        }
    }
}

@Composable
fun VoiceDetailedCard(
    voice: VoiceLicenseEntity,
    isLoading: Boolean,
    onToggleApproval: () -> Unit,
    onInspectAudit: () -> Unit
) {
    val isReady = voice.isApproved && voice.isCommercialUseAllowed

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        border = androidx.compose.foundation.BorderStroke(
            1.dp,
            if (isReady) EmeraldPass.copy(alpha = 0.5f) else CrimsonBlock.copy(alpha = 0.5f)
        ),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Surface(
                        shape = RoundedCornerShape(6.dp),
                        color = if (isReady) IndigoPrimary.copy(alpha = 0.2f) else CrimsonBlock.copy(alpha = 0.2f),
                        border = androidx.compose.foundation.BorderStroke(1.dp, if (isReady) IndigoLight else CrimsonBlock)
                    ) {
                        Text(
                            text = voice.languageCode,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (isReady) IndigoLight else CrimsonBlock,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = voice.languageName,
                        fontWeight = FontWeight.Bold,
                        fontSize = 15.sp,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }

                StatusBadge(
                    text = if (isReady) "ONAYLANDI" else "KİLİTLİ",
                    isSuccess = isReady
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Model Details & Multi-tier licenses
            Text(
                text = "Model: ${voice.modelName}",
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface
            )
            Spacer(modifier = Modifier.height(4.dp))

            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(
                    text = "Motor: ${voice.engineLicense}",
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = "Model: ${voice.modelLicense}",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = if (voice.isCommercialUseAllowed) SkyCyanLight else CrimsonBlock
                )
                Text(
                    text = "Veri Seti: ${voice.datasetLicense.take(24)}",
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "SHA-256: ${voice.modelHashSha256.take(28)}...",
                fontFamily = FontFamily.Monospace,
                fontSize = 10.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            // Audit Findings note
            Spacer(modifier = Modifier.height(8.dp))
            Surface(
                color = if (isReady) MaterialTheme.colorScheme.background.copy(alpha = 0.6f) else CrimsonBlock.copy(alpha = 0.1f),
                shape = RoundedCornerShape(6.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = voice.auditNotes,
                    fontSize = 11.sp,
                    color = if (isReady) MaterialTheme.colorScheme.onSurfaceVariant else CrimsonBlock,
                    modifier = Modifier.padding(8.dp),
                    lineHeight = 15.sp
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Actions & Approval toggle
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedButton(
                    onClick = onInspectAudit,
                    enabled = !isLoading,
                    shape = RoundedCornerShape(8.dp),
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 6.dp)
                ) {
                    Icon(imageVector = Icons.AutoMirrored.Filled.FactCheck, contentDescription = null, modifier = Modifier.size(14.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(text = "Lisans Zincirini İncele", fontSize = 11.sp)
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = if (voice.isApproved) "Onaylı" else "Kapı Kilitli",
                        fontSize = 12.sp,
                        color = if (voice.isApproved) EmeraldPass else CrimsonBlock,
                        fontWeight = FontWeight.Medium
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Switch(
                        checked = voice.isApproved,
                        onCheckedChange = { onToggleApproval() },
                        enabled = !isLoading
                    )
                }
            }
        }
    }
}
