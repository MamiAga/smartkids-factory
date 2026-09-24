package com.example.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.components.CodeViewBlock
import com.example.ui.components.GatingBlockerBanner
import com.example.ui.components.MetricStat
import com.example.ui.components.StatusBadge
import com.example.ui.theme.*

@Composable
fun MasterSpecScreen(
    unapprovedVoiceCount: Int,
    modifier: Modifier = Modifier
) {
    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        contentPadding = PaddingValues(top = 12.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            GatingBlockerBanner(unapprovedCount = unapprovedVoiceCount)
        }

        item {
            Text(
                text = "Ana Teknik Şartname V2",
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = "SmartKids Otonom Öğrenme Ağı • Resmi Doğruluk Kaynağı",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        // Key System Metrics
        item {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                MetricStat(
                    label = "İşlemci Limiti",
                    value = "2 OCPU",
                    subtext = "ARM • 12GB RAM Ücretsiz",
                    icon = Icons.Default.Memory,
                    accentColor = SkyCyan,
                    modifier = Modifier.weight(1f)
                )
                MetricStat(
                    label = "Disk Koruması",
                    value = "200 GB",
                    subtext = "Sıfır sızıntı temizliği",
                    icon = Icons.Default.Storage,
                    accentColor = IndigoLight,
                    modifier = Modifier.weight(1f)
                )
                MetricStat(
                    label = "Maliyet Tavanı",
                    value = "0.00 TL",
                    subtext = "Kesin 0 TL kotası",
                    icon = Icons.Default.AttachMoney,
                    accentColor = EmeraldPass,
                    modifier = Modifier.weight(1f)
                )
            }
        }

        // Cockpit vs Engine Architecture Separation Card
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(imageVector = Icons.Default.FlightTakeoff, contentDescription = null, tint = SkyCyanLight, modifier = Modifier.size(20.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Kokpit ve Motor (Mimari Ayrımı)",
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }
                    Spacer(modifier = Modifier.height(10.dp))
                    Text(
                        text = "• Android Uygulaması = 'Kokpit': İnsan mimar yönetim paneli, yerel Room izleme önbelleği, boru hattı durum denetleyicisi, Bölüm DNA stüdyosu ve Baş Mimar yapay zeka konsolu.\n\n" +
                                "• Oracle VPS = 'Uçak Motoru': 10 dilde çalışan otonom üretim fabrikası (Headless Docker konteynerleri: PostgreSQL 16, Redis 7, Python Celery orkestratörü, Piper TTS ONNX motorları, FFmpeg deterministik render motoru, YouTube OAuth parçalı yükleyicisi).\n\n" +
                                "• Senkronizasyon Sınırı: Android kokpiti Oracle sunucusu ile güvenli REST / mTLS protokolleri üzerinden haberleşir; kuyruk derinliğini izler, logları görüntüler ve toplu işleri tetikler.",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        lineHeight = 17.sp
                    )
                }
            }
        }

        // Locked Decisions Overview
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "🔒 Kilitli Master Kararlar (Değiştirilemez Kurallar)",
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    val masterRules = listOf(
                        "ORACLE OCI ALWAYS FREE" to "2 OCPU + 12GB RAM + 200GB Blok Depolama. Görev başına iş parçacığı kesin olarak 1 ile sınırlı.",
                        "0 TL ÇİFT KATMANLI KORUMA" to "Uygulama İçi CostGuard denetimi + Cloud compartman kota kilidi (0.00 TL tavanı).",
                        "GEMINI 0 TL STRATEJİSİ" to "gemini-3.5-flash (QA ve denetim kapısı) ve gemini-3.5-flash-lite (lokalizasyon/metadata). 3.1 Pro & Search kaldırıldı.",
                        "STATİK SES KÜTÜĞÜ" to "Lisans doğrulaması statik SHA-256 denetimine bağlandı; çalışma anı web araması kaldırıldı.",
                        "TÜRKÇE (TR) ENGELİ" to "tr_TR-dfki-medium (CC-BY-NC 4.0 ticari olmayan) kilitli. Çözüm: CC0/MIT model (tr_TR-fahrettin) ile değişim.",
                        "YOUTUBE API 100/GÜN" to "videos.insert: 100 çağrı/gün (1 birim/çağrı). 10-20 video/gün tek API projesi kotasına tam uygun.",
                        "YOUTUBE OAUTH (10 KANAL)" to "EN, ES, DE, FR, PT, AR, HI, ZH, JA, TR dilleri için bağımsız offline refresh_token.",
                        "TTS KESİN KARAR" to "XTTS-v2 ticari olmayan CPML lisansı nedeniyle REDDEDİLDİ. Piper Engine (GPL-3.0) kabul edildi.",
                        "DETERMİNİSTİK RENDER" to "seed = SHA256(episode_id + lang + version) -> Tekrarlarda %100 aynı video/ses çıktısı.",
                        "BÖLÜM DNA ŞEMASI" to "Enum format_type, sınırlandırılmış etkileşim duraklamaları, beyaz listedeki varlık kimlikleri.",
                        "TEKNİK & EĞİTSEL QA" to "FFprobe akış ve kodek denetimi + sesli söylenen sayı ile görsel sayı eşitlik doğrulaması.",
                        "GÜVENLİ MP4 SİLME" to "upload -> video_id -> YouTube işleme başarılı teyidi -> DB commit -> yerel MP4 silme (0 bayt sızıntı)."
                    )

                    masterRules.forEach { (title, desc) ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            StatusBadge(text = "KİLİTLİ", isSuccess = true)
                            Spacer(modifier = Modifier.width(8.dp))
                            Column {
                                Text(text = title, fontSize = 12.sp, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurface)
                                Text(text = desc, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                }
            }
        }

        // Section: Python Orchestrator Architecture
        item {
            CodeViewBlock(
                title = "Oracle VPS Python Orchestrator (orchestrator.py)",
                code = """# SmartKids Headless Factory Orchestrator (Python 3.11 / Redis / Celery)
import hashlib
import json
import os
import psycopg2
from celery import Celery
import requests

app = Celery('smartkids_factory', broker='redis://redis:6379/0', backend='redis://redis:6379/1')

# STRICT CONCURRENCY BOUNDARIES (2 OCPU / 12GB RAM)
# TTS: concurrency=1 | Render: concurrency=1 | Uploader: concurrency=1

def compute_seed(episode_id: str, lang: str, version: str = "2.0.0") -> str:
    payload = f"{episode_id}:{lang}:{version}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_language_pipeline(self, episode_id: str, lang: str):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cursor = conn.cursor()
    
    # 1. Check Voice License Gate
    cursor.execute(
        "SELECT model_path, license, commercial_use, approved FROM piper_voice_registry WHERE language = %s;",
        (lang,)
    )
    voice = cursor.fetchone()
    if not voice or not voice[2] or not voice[3]:
        raise PermissionError(f"PIPELINE GATE BLOCKED: Language {lang} voice not commercial safe ({voice[1] if voice else 'None'})")

    seed = compute_seed(episode_id, lang)
    
    # 2. Localize Script with gemini-3.5-flash-lite
    # 3. Piper TTS Worker (CPU bounded, ONNX native)
    # 4. Deterministic FFmpeg Render (1080p60, h264_arm64, capped 120 cd/m2)
    # 5. Dual QA Gate (Technical FFprobe + Educational Invariant)
    # 6. YouTube Resumable OAuth Upload (chunk size 4MB)
    # 7. Zero Disk Leak: Verify upload -> commit DB -> unlink(local_mp4)
    conn.close()
    return {"status": "PUBLISHED", "seed": seed}"""
            )
        }

        // Section: PostgreSQL DDL
        item {
            CodeViewBlock(
                title = "PostgreSQL Schema DDL (Master V2)",
                code = """-- SmartKids Autonomous Learning Network - Canonical V2 DDL
CREATE TABLE episode_dna (
    episode_id VARCHAR(64) PRIMARY KEY,
    version VARCHAR(16) NOT NULL DEFAULT '2.0.0',
    age_group VARCHAR(16) NOT NULL CHECK (age_group IN ('2-4', '4-6', '6-8')),
    learning_objective TEXT NOT NULL,
    format_type VARCHAR(32) NOT NULL CHECK (format_type IN ('NURSERY_RHYME', 'COUNTING', 'CONCEPT_EXPLORATION', 'INTERACTIVE_QUIZ')),
    difficulty VARCHAR(16) NOT NULL DEFAULT 'BEGINNER',
    target_duration_sec INT NOT NULL,
    min_duration_sec INT NOT NULL,
    max_duration_sec INT NOT NULL,
    characters JSONB NOT NULL,
    visual_style TEXT NOT NULL,
    music_profile TEXT NOT NULL,
    scenes JSONB NOT NULL,
    safety_profile JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE piper_voice_registry (
    voice_id VARCHAR(64) PRIMARY KEY,
    language VARCHAR(8) NOT NULL CHECK (language IN ('EN','ES','DE','FR','PT','AR','HI','ZH','JA','TR')),
    model_path TEXT NOT NULL,
    model_hash VARCHAR(64) NOT NULL,
    license VARCHAR(64) NOT NULL,
    commercial_use BOOLEAN NOT NULL DEFAULT FALSE,
    attribution_required BOOLEAN NOT NULL DEFAULT TRUE,
    attribution_text TEXT,
    source TEXT NOT NULL,
    approved BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE pipeline_jobs (
    job_id VARCHAR(64) PRIMARY KEY,
    episode_id VARCHAR(64) REFERENCES episode_dna(episode_id),
    language VARCHAR(8) NOT NULL,
    state VARCHAR(32) NOT NULL CHECK (state IN ('RENDERED','UPLOADING','UPLOADED','PROCESSING','PROCESSED','PUBLISHED','DELETE_LOCAL_FILE','QA_FAILED','QUARANTINED')),
    deterministic_seed VARCHAR(64) NOT NULL,
    youtube_video_id VARCHAR(32),
    cost_usd NUMERIC(6,4) DEFAULT 0.0000 CHECK (cost_usd = 0.0),
    local_file_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Invariant Enforcement: Disallow job execution if voice is not approved
CREATE OR REPLACE FUNCTION check_voice_approval()
RETURNS TRIGGER AS ${'$'}${'$'}
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM piper_voice_registry 
        WHERE language = NEW.language AND commercial_use = TRUE AND approved = TRUE
    ) THEN
        RAISE EXCEPTION 'PIPELINE GATE BLOCKED: Commercial-safe approved Piper voice missing for language %', NEW.language;
    END IF;
    RETURN NEW;
END;
${'$'}${'$'} LANGUAGE plpgsql;

CREATE TRIGGER trg_check_voice BEFORE INSERT ON pipeline_jobs
FOR EACH ROW EXECUTE FUNCTION check_voice_approval();"""
            )
        }

        // Section: Zero Cost Guard & Cloud Architecture
        item {
            CodeViewBlock(
                title = "Oracle OCI Always Free Docker Compose (2 OCPU Bounded)",
                code = """# Docker Compose for Oracle OCI Always Free ARM (2 OCPU / 12GB RAM)
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    deploy:
      resources:
        limits:
          cpus: '0.30'
          memory: 2G
    volumes:
      - /mnt/oci_block/pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    deploy:
      resources:
        limits:
          cpus: '0.15'
          memory: 512M

  orchestrator:
    build: ./services/orchestrator
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 1G
    environment:
      - GEMINI_MODEL_QA=gemini-3.5-flash
      - GEMINI_MODEL_LOC=gemini-3.5-flash-lite

  piper_tts_worker:
    build: ./workers/piper_server
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 2.5G
    environment:
      - COMMERCIAL_SAFETY_GATE=STRICT
      - XTTS_BANNED=TRUE

  render_worker:
    build: ./workers/ffmpeg_render
    deploy:
      resources:
        limits:
          cpus: '0.60'
          memory: 4G
    environment:
      - HARDWARE_ACCEL=NONE_ARM64
      - SEED_DETERMINISTIC=TRUE

  youtube_worker:
    build: ./workers/youtube_uploader
    deploy:
      resources:
        limits:
          cpus: '0.20'
          memory: 1G
    environment:
      - INSERT_QUOTA_LIMIT_PER_DAY=100
      - SAFE_DELETE_VERIFIED=TRUE"""
            )
        }
    }
}
