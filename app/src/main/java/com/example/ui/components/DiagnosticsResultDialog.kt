package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import com.example.data.remote.FullDiagnosticsResult
import com.example.data.remote.ServiceCheckResult
import com.example.data.remote.ServiceStatus

@Composable
fun DiagnosticsResultDialog(
    diagnosticsResult: FullDiagnosticsResult,
    onDismiss: () -> Unit
) {
    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(24.dp),
            color = MaterialTheme.colorScheme.surface,
            tonalElevation = 6.dp,
            modifier = Modifier
                .fillMaxWidth()
                .padding(8.dp)
                .testTag("dialog_diagnostics_result")
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(20.dp)
            ) {
                // Header
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    val headerColor = if (diagnosticsResult.allHealthy) Color(0xFF2E7D32) else Color(0xFFC62828)
                    Icon(
                        imageVector = if (diagnosticsResult.allHealthy) Icons.Default.CheckCircle else Icons.Default.Warning,
                        contentDescription = null,
                        tint = headerColor,
                        modifier = Modifier.size(28.dp)
                    )
                    Column {
                        Text(
                            text = if (diagnosticsResult.allHealthy) "SİSTEM TESTİ BAŞARILI" else "BAĞLANTI UYARISI",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = headerColor
                        )
                        Text(
                            text = if (diagnosticsResult.allHealthy) "Üretim için tüm kapılar açık" else "Bazı servislerde dikkat gereken durumlar var",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Servisler Listesi
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    items(diagnosticsResult.results) { item ->
                        ServiceResultRow(item)
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Özet Mesajı
                Surface(
                    shape = RoundedCornerShape(12.dp),
                    color = if (diagnosticsResult.allHealthy) Color(0xFFE8F5E9) else Color(0xFFFFF3E0),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = diagnosticsResult.summaryMessage,
                        style = MaterialTheme.typography.bodySmall,
                        fontWeight = FontWeight.Medium,
                        color = if (diagnosticsResult.allHealthy) Color(0xFF1B5E20) else Color(0xFFE65100),
                        modifier = Modifier.padding(12.dp)
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                Button(
                    onClick = onDismiss,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp)
                        .testTag("btn_close_diagnostics"),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("TAMAM / ANLADIM")
                }
            }
        }
    }
}

@Composable
private fun ServiceResultRow(result: ServiceCheckResult) {
    val (statusIcon, iconColor, bgColor) = when (result.status) {
        ServiceStatus.SUCCESS -> Triple(Icons.Default.CheckCircle, Color(0xFF2E7D32), Color(0xFFE8F5E9))
        ServiceStatus.WARNING -> Triple(Icons.Default.Warning, Color(0xFFF57F17), Color(0xFFFFFDE7))
        ServiceStatus.FAILED -> Triple(Icons.Default.Error, Color(0xFFC62828), Color(0xFFFFEBEE))
        else -> Triple(Icons.Default.CheckCircle, Color.Gray, Color.LightGray.copy(alpha = 0.2f))
    }

    Surface(
        shape = RoundedCornerShape(14.dp),
        color = bgColor,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .padding(12.dp)
                .fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.weight(1f)
            ) {
                Icon(
                    imageVector = statusIcon,
                    contentDescription = null,
                    tint = iconColor,
                    modifier = Modifier.size(24.dp)
                )
                Column {
                    Text(
                        text = result.serviceName,
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = result.message,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    if (result.detail != null) {
                        Text(
                            text = result.detail,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.outline,
                            maxLines = 2
                        )
                    }
                }
            }

            if (result.latencyMs > 0) {
                Surface(
                    shape = CircleShape,
                    color = Color.Black.copy(alpha = 0.05f)
                ) {
                    Text(
                        text = "${result.latencyMs} ms",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
            }
        }
    }
}
