package com.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.MenuBook
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.ui.components.AppTopBar
import com.example.ui.screens.*
import com.example.ui.theme.MyApplicationTheme
import com.example.ui.viewmodel.AppTab
import com.example.ui.viewmodel.MainViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.colorMode = android.content.pm.ActivityInfo.COLOR_MODE_DEFAULT
        window.setFormat(android.graphics.PixelFormat.TRANSLUCENT)
        enableEdgeToEdge()
        setContent {
            MyApplicationTheme {
                MainApp()
            }
        }
    }
}

@Composable
fun MainApp(mainViewModel: MainViewModel = viewModel()) {
    val currentTab by mainViewModel.currentTab.collectAsStateWithLifecycle()
    val voices by mainViewModel.voices.collectAsStateWithLifecycle()
    val episodes by mainViewModel.episodes.collectAsStateWithLifecycle()
    val jobs by mainViewModel.jobs.collectAsStateWithLifecycle()
    val chatMessages by mainViewModel.chatMessages.collectAsStateWithLifecycle()
    val unapprovedVoiceCount by mainViewModel.unapprovedOrBlockedCount.collectAsStateWithLifecycle()
    val automationControl by mainViewModel.automationControl.collectAsStateWithLifecycle()
    val systemEvents by mainViewModel.systemEvents.collectAsStateWithLifecycle()

    val chatInput by mainViewModel.chatInput.collectAsStateWithLifecycle()
    val selectedChatModel by mainViewModel.selectedChatModel.collectAsStateWithLifecycle()
    val isAiLoading by mainViewModel.isAiLoading.collectAsStateWithLifecycle()
    val notification by mainViewModel.notification.collectAsStateWithLifecycle()
    val inspectedVoiceAudit by mainViewModel.inspectedVoiceAudit.collectAsStateWithLifecycle()

    val selectedEpisode by mainViewModel.selectedEpisode.collectAsStateWithLifecycle()
    val qaResult by mainViewModel.qaResult.collectAsStateWithLifecycle()
    val diagnosticsResult by mainViewModel.diagnosticsState.collectAsStateWithLifecycle()
    val isDiagnosing by mainViewModel.isDiagnosing.collectAsStateWithLifecycle()

    val snackbarHostState = remember { SnackbarHostState() }

    // Dialog showing full diagnostics results
    diagnosticsResult?.let { result ->
        com.example.ui.components.DiagnosticsResultDialog(
            diagnosticsResult = result,
            onDismiss = { mainViewModel.dismissDiagnosticsDialog() }
        )
    }

    LaunchedEffect(notification) {
        notification?.let {
            snackbarHostState.showSnackbar(
                message = it.message,
                duration = SnackbarDuration.Short
            )
            mainViewModel.clearNotification()
        }
    }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        topBar = {
            AppTopBar(
                unapprovedCount = unapprovedVoiceCount
            )
        },
        bottomBar = {
            NavigationBar {
                NavigationBarItem(
                    selected = currentTab == AppTab.CONTROL_CENTER,
                    onClick = { mainViewModel.selectTab(AppTab.CONTROL_CENTER) },
                    icon = { Icon(imageVector = Icons.Default.PowerSettingsNew, contentDescription = "Bulut Kumandası") },
                    label = { Text("Kumanda") }
                )
                NavigationBarItem(
                    selected = currentTab == AppTab.PIPELINE,
                    onClick = { mainViewModel.selectTab(AppTab.PIPELINE) },
                    icon = { Icon(imageVector = Icons.Default.PrecisionManufacturing, contentDescription = "İş Akışı") },
                    label = { Text("İş Akışı") }
                )
                NavigationBarItem(
                    selected = currentTab == AppTab.EPISODE_DNA,
                    onClick = { mainViewModel.selectTab(AppTab.EPISODE_DNA) },
                    icon = { Icon(imageVector = Icons.AutoMirrored.Filled.MenuBook, contentDescription = "Bölüm DNA") },
                    label = { Text("DNA") }
                )
                NavigationBarItem(
                    selected = currentTab == AppTab.VOICE_REGISTRY,
                    onClick = { mainViewModel.selectTab(AppTab.VOICE_REGISTRY) },
                    icon = {
                        BadgedBox(
                            badge = {
                                if (unapprovedVoiceCount > 0) {
                                    Badge { Text("$unapprovedVoiceCount") }
                                }
                            }
                        ) {
                            Icon(imageVector = Icons.Default.RecordVoiceOver, contentDescription = "Sesler")
                        }
                    },
                    label = { Text("Sesler") }
                )
                NavigationBarItem(
                    selected = currentTab == AppTab.AI_ARCHITECT,
                    onClick = { mainViewModel.selectTab(AppTab.AI_ARCHITECT) },
                    icon = { Icon(imageVector = Icons.Default.Psychology, contentDescription = "Fabrika Asistanı") },
                    label = { Text("Asistan") }
                )
            }
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { innerPadding ->
        Box(modifier = Modifier.padding(innerPadding)) {
            when (currentTab) {
                AppTab.CONTROL_CENTER -> ControlCenterScreen(
                    automationControl = automationControl,
                    jobs = jobs,
                    events = systemEvents,
                    onToggleFactory = { mainViewModel.toggleFactory(it) },
                    onUpdateDailyTarget = { mainViewModel.updateDailyTarget(it) },
                    onToggleLanguage = { mainViewModel.toggleActiveLanguage(it) },
                    onRunDiagnostics = { mainViewModel.runConnectivityDiagnostics() },
                    isDiagnosing = isDiagnosing,
                    diagnosticsResult = diagnosticsResult
                )
                AppTab.VOICE_REGISTRY -> VoiceRegistryScreen(
                    voices = voices,
                    unapprovedCount = unapprovedVoiceCount,
                    inspectedAuditRecord = inspectedVoiceAudit,
                    isLoading = isAiLoading,
                    onToggleApproval = { mainViewModel.toggleVoiceApproval(it) },
                    onInspectAudit = { mainViewModel.inspectVoiceStaticAudit(it) },
                    onDismissAuditDialog = { mainViewModel.clearInspectedVoiceAudit() }
                )
                AppTab.EPISODE_DNA -> EpisodeDnaScreen(
                    episodes = episodes,
                    selectedEpisode = selectedEpisode,
                    qaResult = qaResult,
                    isLoading = isAiLoading,
                    onSelectEpisode = { mainViewModel.selectEpisode(it) },
                    onRunQa = { mainViewModel.runEducationalQa(it) },
                    onGenerateNew = { mainViewModel.generateNewEpisodeDna(it) }
                )
                AppTab.PIPELINE -> PipelineScreen(
                    jobs = jobs,
                    episodes = episodes,
                    unapprovedVoiceCount = unapprovedVoiceCount,
                    onStepJob = { mainViewModel.stepPipelineJob(it) },
                    onCreateJob = { ep, lang -> mainViewModel.createPipelineJobForLanguage(ep, lang) }
                )
                AppTab.AI_ARCHITECT -> ChatbotScreen(
                    messages = chatMessages,
                    chatInput = chatInput,
                    selectedModel = selectedChatModel,
                    isLoading = isAiLoading,
                    onInputChange = { mainViewModel.setChatInput(it) },
                    onModelChange = { mainViewModel.setSelectedChatModel(it) },
                    onSendMessage = { mainViewModel.sendChat() },
                    onClearChat = { mainViewModel.clearChat() }
                )
            }
        }
    }
}
