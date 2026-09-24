package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import com.example.ui.components.CodeViewBlock
import com.example.ui.components.StatusBadge
import com.example.ui.theme.*

@Composable
fun EpisodeDnaScreen(
    episodes: List<EpisodeDnaEntity>,
    selectedEpisode: EpisodeDnaEntity?,
    qaResult: String?,
    isLoading: Boolean,
    onSelectEpisode: (EpisodeDnaEntity?) -> Unit,
    onRunQa: (EpisodeDnaEntity) -> Unit,
    onGenerateNew: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    var showDialog by remember { mutableStateOf(false) }
    var topicPrompt by remember { mutableStateOf("") }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        contentPadding = PaddingValues(top = 12.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "Bölüm DNA Stüdyosu",
                        style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.onBackground
                    )
                    Text(
                        text = "Müfredat Şartnamesi ve Eğitsel Kalite (QA) Kapısı",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Button(
                    onClick = { showDialog = true },
                    enabled = !isLoading,
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = IndigoPrimary)
                ) {
                    Icon(imageVector = Icons.Default.AutoAwesome, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(text = "Yeni DNA", fontSize = 12.sp)
                }
            }
        }

        // Selected Episode Inspector (if selected)
        if (selectedEpisode != null) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                    border = androidx.compose.foundation.BorderStroke(1.dp, IndigoLight),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = selectedEpisode.title,
                                fontWeight = FontWeight.Bold,
                                fontSize = 16.sp,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            IconButton(onClick = { onSelectEpisode(null) }) {
                                Icon(imageVector = Icons.Default.Close, contentDescription = "Kapat")
                            }
                        }

                        Spacer(modifier = Modifier.height(6.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            StatusBadge(text = "Yaş: ${selectedEpisode.ageGroup}", isSuccess = true)
                            StatusBadge(text = selectedEpisode.formatType, isSuccess = true)
                            StatusBadge(
                                text = if (selectedEpisode.qaStatus == "PASSED_QA") "QA GEÇTİ" else if (selectedEpisode.qaStatus == "FAILED_QA") "QA BAŞARISIZ" else "QA BEKLİYOR",
                                isSuccess = selectedEpisode.qaStatus == "PASSED_QA",
                                isWarning = selectedEpisode.qaStatus == "PENDING_QA"
                            )
                        }

                        Spacer(modifier = Modifier.height(10.dp))
                        Text(
                            text = "Eğitim Hedefi: ${selectedEpisode.learningObjective}",
                            fontSize = 13.sp,
                            color = MaterialTheme.colorScheme.onSurface,
                            lineHeight = 18.sp
                        )

                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = "Görsel Stil: ${selectedEpisode.visualStyle}",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = "Müzik Profili: ${selectedEpisode.musicProfile}",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = "Hedef Süre: ${selectedEpisode.targetDurationSeconds} sn (Aralık: ${selectedEpisode.minDurationSeconds}-${selectedEpisode.maxDurationSeconds} sn)",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )

                        Spacer(modifier = Modifier.height(12.dp))

                        // QA Action
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Button(
                                onClick = { onRunQa(selectedEpisode) },
                                enabled = !isLoading,
                                shape = RoundedCornerShape(8.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = VioletThinking)
                            ) {
                                Icon(imageVector = Icons.Default.Psychology, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(text = "Eğitsel Kalite (QA) Analizini Başlat", fontSize = 12.sp)
                            }
                        }

                        // QA result box
                        if (qaResult != null) {
                            Spacer(modifier = Modifier.height(12.dp))
                            Surface(
                                color = MaterialTheme.colorScheme.background,
                                shape = RoundedCornerShape(8.dp),
                                border = androidx.compose.foundation.BorderStroke(1.dp, VioletThinking.copy(alpha = 0.5f)),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Column(modifier = Modifier.padding(10.dp)) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(imageVector = Icons.Default.Verified, contentDescription = null, tint = VioletThinking, modifier = Modifier.size(16.dp))
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Text(text = "Eğitsel Değişmezlik Doğrulama Raporu:", fontWeight = FontWeight.Bold, fontSize = 12.sp, color = VioletThinking)
                                    }
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(text = qaResult, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurface, lineHeight = 16.sp)
                                }
                            }
                        }
                    }
                }
            }
        }

        item {
            Text(
                text = "Müfredat Bölümleri",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onBackground
            )
        }

        // Episode List
        items(episodes, key = { it.episodeId }) { episode ->
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onSelectEpisode(episode) },
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.3f)),
                shape = RoundedCornerShape(10.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(14.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = episode.episodeId,
                                fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace,
                                color = IndigoLight
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            StatusBadge(text = "Yaş ${episode.ageGroup}", isSuccess = true)
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = episode.title,
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = episode.learningObjective,
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 2
                        )
                    }

                    Column(horizontalAlignment = Alignment.End) {
                        StatusBadge(
                            text = if (episode.qaStatus == "PASSED_QA") "QA GEÇTİ" else if (episode.qaStatus == "FAILED_QA") "QA BAŞARISIZ" else "QA BEKLİYOR",
                            isSuccess = episode.qaStatus == "PASSED_QA",
                            isWarning = episode.qaStatus == "PENDING_QA"
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Icon(imageVector = Icons.Default.ChevronRight, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }

        // Episode DNA Schema Specification
        item {
            CodeViewBlock(
                title = "Bölüm DNA Resmi JSON Şeması (Canonical Schema)",
                code = """{
  "${'$'}schema": "https://smartkids.network/schemas/episode_dna.v2.json",
  "episode_id": "EP-SAFARI-001",
  "version": "2.0.0",
  "age_group": "2-4",
  "format_type": "CONCEPT_EXPLORATION",
  "learning_objective": "Identify 5 primary colors paired with animal sounds",
  "difficulty": "BEGINNER",
  "target_duration_seconds": 120,
  "characters": [
    { "id": "milo_monkey", "name": "Milo the Monkey", "role": "Guide" }
  ],
  "visual_style": "Pastel Flat Vector, 60fps FFmpeg",
  "music_profile": "Uplifting marimba + ukulele, 105 BPM",
  "scenes": [
    {
      "scene_number": 1,
      "speech": "Look! 1 Red Apple on the branch!",
      "visual_items": 1,
      "target_color": "Red",
      "interaction_pause_sec": 2.2
    }
  ],
  "safety_profile": {
    "zero_strobe": true,
    "max_contrast_ratio": "4.5:1",
    "calm_auditory_cues": true
  }
}"""
            )
        }
    }

    if (showDialog) {
        AlertDialog(
            onDismissRequest = { showDialog = false },
            title = { Text("Yeni Bölüm DNA'sı Oluştur (Yapay Zeka)") },
            text = {
                Column {
                    Text(
                        "Eğitsel konuyu veya müfredat hedefini girin (örnek: 'Geometrik Şekiller 1-5' veya 'Bahçe Böcekleri ve Renkler'):",
                        fontSize = 13.sp
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    OutlinedTextField(
                        value = topicPrompt,
                        onValueChange = { topicPrompt = it },
                        label = { Text("Eğitsel Konu / Tema") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (topicPrompt.isNotBlank()) {
                            onGenerateNew(topicPrompt)
                            showDialog = false
                            topicPrompt = ""
                        }
                    }
                ) {
                    Text("Oluştur")
                }
            },
            dismissButton = {
                TextButton(onClick = { showDialog = false }) {
                    Text("İptal")
                }
            }
        )
    }
}
