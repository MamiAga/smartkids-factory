package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
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
import com.example.data.api.GeminiClient
import com.example.data.local.ChatMessageEntity
import com.example.ui.components.StatusBadge
import com.example.ui.theme.*

@Composable
fun ChatbotScreen(
    messages: List<ChatMessageEntity>,
    chatInput: String,
    selectedModel: String,
    isLoading: Boolean,
    onInputChange: (String) -> Unit,
    onModelChange: (String) -> Unit,
    onSendMessage: () -> Unit,
    onClearChat: () -> Unit,
    modifier: Modifier = Modifier
) {
    val listState = rememberLazyListState()

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp, vertical = 8.dp)
    ) {
        // Chatbot Header & Role Definition
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = IndigoPrimary.copy(alpha = 0.2f),
                        modifier = Modifier.size(36.dp)
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Icon(
                                imageVector = Icons.Default.Psychology,
                                contentDescription = null,
                                tint = IndigoLight,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }
                    Spacer(modifier = Modifier.width(10.dp))
                    Column {
                        Text(
                            text = "Baş Mimar Yapay Zeka Danışmanı",
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Text(
                            text = "İnsan Mimar Danışmanı • 0 TL Ücretsiz Katman Stratejisi",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                IconButton(onClick = onClearChat) {
                    Icon(
                        imageVector = Icons.Default.DeleteOutline,
                        contentDescription = "Geçmişi Temizle",
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Production Model Selector (Strictly gemini-3.5-flash & gemini-3.5-flash-lite)
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            // gemini-3.5-flash (Standard & QA Engine)
            FilterChip(
                selected = selectedModel == GeminiClient.MODEL_FLASH,
                onClick = { onModelChange(GeminiClient.MODEL_FLASH) },
                label = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(imageVector = Icons.Default.AutoAwesome, contentDescription = null, modifier = Modifier.size(14.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("gemini-3.6-flash (Baş Mimar)", fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                    }
                },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = SkyCyanLight.copy(alpha = 0.2f),
                    selectedLabelColor = SkyCyanLight
                )
            )

            // gemini-3.5-flash-lite (High Volume Localization)
            FilterChip(
                selected = selectedModel == GeminiClient.MODEL_FLASH_LITE,
                onClick = { onModelChange(GeminiClient.MODEL_FLASH_LITE) },
                label = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(imageVector = Icons.Default.Bolt, contentDescription = null, modifier = Modifier.size(14.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("gemini-3.5-flash-lite (Yerelleştirme)", fontSize = 11.sp)
                    }
                },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = EmeraldPass.copy(alpha = 0.2f),
                    selectedLabelColor = EmeraldPass
                )
            )
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Quick Suggestion Chips
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            val suggestions = listOf(
                "Türkçe (TR) Piper Ses Engeli ve Çözümü",
                "Oracle VPS İş Parçacığı Sınırları (2 OCPU)",
                "Kokpit ve Üretim Fabrikası Ayrımı",
                "Sıfır Disk Sızıntısı ve MP4 Temizliği"
            )
            suggestions.forEach { suggestion ->
                AssistChip(
                    onClick = { onInputChange(suggestion) },
                    label = { Text(suggestion, fontSize = 11.sp) },
                    shape = RoundedCornerShape(16.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Message List
        LazyColumn(
            state = listState,
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            if (messages.isEmpty()) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 36.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(
                                imageVector = Icons.Default.SmartToy,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
                                modifier = Modifier.size(44.dp)
                            )
                            Spacer(modifier = Modifier.height(10.dp))
                            Text(
                                text = "Baş Mimar Konsolu",
                                fontWeight = FontWeight.Bold,
                                fontSize = 15.sp,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "Oracle VPS Docker çalışanları, 10 dilde Piper ses lisansları veya Kokpit-Fabrika senkronizasyonu hakkında sorularınızı danışın.",
                                fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                                lineHeight = 16.sp
                            )
                        }
                    }
                }
            }

            items(messages, key = { it.id }) { msg ->
                val isUser = msg.role == "user"
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalAlignment = if (isUser) Alignment.End else Alignment.Start
                ) {
                    // Role / Badge Header
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = if (isUser) "İnsan Baş Mimar" else "Yapay Zeka Mimar Danışmanı",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = if (isUser) IndigoLight else SkyCyanLight
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        StatusBadge(
                            text = if (msg.modelUsed.contains("lite")) "FLASH-LITE" else "FLASH",
                            isSuccess = true
                        )
                    }

                    Spacer(modifier = Modifier.height(4.dp))

                    Surface(
                        shape = RoundedCornerShape(
                            topStart = 12.dp,
                            topEnd = 12.dp,
                            bottomStart = if (isUser) 12.dp else 2.dp,
                            bottomEnd = if (isUser) 2.dp else 12.dp
                        ),
                        color = if (isUser) IndigoPrimary else CardNavy,
                        border = androidx.compose.foundation.BorderStroke(
                            1.dp,
                            if (isUser) IndigoLight.copy(alpha = 0.5f) else BorderNavy
                        ),
                        modifier = Modifier.widthIn(max = 320.dp)
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text(
                                text = msg.content,
                                fontSize = 13.sp,
                                color = TextPrimary,
                                lineHeight = 18.sp
                            )
                        }
                    }
                }
            }

            if (isLoading) {
                item {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(vertical = 8.dp)
                    ) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp, color = SkyCyanLight)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Mimari kurallar ve kısıtlamalar analiz ediliyor ($selectedModel)...",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Input Bar
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = chatInput,
                onValueChange = onInputChange,
                placeholder = { Text("Docker çalışanları, Piper sesleri veya şema DDL hakkında danışın...", fontSize = 12.sp) },
                modifier = Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(24.dp)),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = SkyCyanLight,
                    unfocusedBorderColor = MaterialTheme.colorScheme.outline
                ),
                maxLines = 3,
                textStyle = LocalTextStyle.current.copy(fontSize = 13.sp)
            )

            Spacer(modifier = Modifier.width(8.dp))

            IconButton(
                onClick = onSendMessage,
                enabled = chatInput.isNotBlank() && !isLoading,
                modifier = Modifier
                    .background(
                        if (chatInput.isNotBlank() && !isLoading) IndigoPrimary else MaterialTheme.colorScheme.surfaceVariant,
                        shape = RoundedCornerShape(20.dp)
                    )
                    .size(44.dp)
            ) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.Send,
                    contentDescription = "Gönder",
                    tint = if (chatInput.isNotBlank() && !isLoading) Color.White else MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}
