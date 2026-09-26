# SmartKids Factory — Denetim ve Düzeltme Raporu (26 Eylül 2026)

Temel: GitHub `main` @ `be60888` (yerel klasörle aynı). Bu rapordaki düzeltmeler henüz **push edilmedi**.

## 1. Bulunan mantık hataları

### Kritik (sistemi "çalışan" yapmayı engelleyenler)

| # | Sorun | Sonucu |
|---|---|---|
| 1 | `smartkids_factory.yml` her saat çalışıyor, `enabled=true` ise **her saat** üretiyordu. `schedule_time`, `daily_master_episodes` hiç kontrol edilmiyordu. | START'tan sonra günde 24 kez aynı video YouTube'a yüklenecek, kota birkaç yüklemede bitecekti. |
| 2 | Bölüm sabit: her çalışmada `EP-COLORS-5-V1`. | Fabrika hiç yeni içerik üretemiyordu; sadece aynı videonun kopyaları. |
| 3 | Idempotency yok: `job_id` deterministik ama yüklemeden önce kontrol edilmiyordu. | Her tekrar = yeni YouTube videosu; Supabase satırı ise üzerine yazılıyordu (eski video ID kayboluyordu). |
| 4 | Android START iki şeyi birden yapıyordu: `enabled=true` + `production_pipeline.yml` dispatch. | Aynı anda iki üretim hattı (dispatch + saatlik cron) → çift yükleme. |
| 5 | `production_runner` sonucu `status` anahtarı döndürmüyordu; orkestratör `status == "SUCCESS"` bekliyordu. | Başarılı her üretim `EPISODE_PRODUCTION_ERROR` olarak loglanıyor, `youtube_publications` hiç yazılmıyordu. |
| 6 | Dil izolasyonu yok: EN dışı dil `ValueError` fırlatıyor, orkestratör yakalamıyordu. | Android'den ES açılınca tüm döngü (EN dahil) çöküyordu. |
| 7 | Gerçek progress/heartbeat yoktu: runner `pipeline_jobs`'a yalnızca **en sonda** yazıyordu; `production_pipeline.yml` hiç heartbeat yazmıyordu. | Android'deki ilerleme çubuğu gerçek aşamayı gösteremezdi. |
| 8 | Android durum adları (`PLANNED/TTS_READY/RENDERED…`) backend durumlarıyla (`TTS_SYNTHESIS/RENDERING/QA_TECHNICAL…`) uyuşmuyordu. | Backend'in her aşaması Android'de "5/60" görünüyordu. |

### Sahte veri kalıntıları (Android)
- Uygulama ilk açılışta 3 sahte iş ekliyordu (`yt_demo_en_safari1` vb.) → "üretilen video" sayacı sahte artıyordu.
- "Aşamayı İlerlet" butonu işi telefonda sahte durumlara geçiriyor, sahte video ID ve "Oracle 200GB disk" logu yazıyordu.
- START/dispatch sonrası yerelde sahte `PLANNED` iş oluşturuluyordu → hiç bitmeyen "aktif iş".
- Supabase yazma hatası sessizce yutuluyordu → UI "ÜRETİM AÇIK" derken bulut kapalı kalabiliyordu.
- Zamanlama (`schedule_time`) değişikliği sadece telefonda kalıyor, Supabase'e hiç gitmiyordu.

### Diğer
- Kota hatası (`quotaExceeded`) ayırt edilmiyordu; `QUOTA_PAUSED` yalnızca şemada vardı.
- Teknik QA `assert` ile yapılıyordu (`python -O` ile tamamen devre dışı kalır).
- Kanıt/lisans: `piper_voice_registry` seed'indeki `model_sha256` değerleri gerçek değil (ör. `e3b0c442…` boş dosyanın hash'i, `6b86b273…` = sha256("1")). ES (sharvard) ve PT (edresson) lisansları model kartından ayrıca doğrulanmalı.
- Cron `0 * * * *`: GitHub, saat başı zamanlamaları sık geciktirir/atlar.
- Eski mimari kodu hâlâ repoda: `backend/orchestrator/` (Celery/Redis), `backend/docker-compose.yml`, `backend/benchmarks/benchmark_oracle_arm64.py`, `backend/workers/*`. Üretimde kullanılmıyor; silinebilir.

## 2. Yapılan düzeltmeler

**Backend**
- `backend/engine/curriculum.py` (yeni): 8 bölümlük EN müfredatı (renkler ×2, sayılar 1–5 / 6–10, şekiller, çiftlik hayvanları, meyveler, zıt kavramlar). Hepsi aynı pedagojik şablon ve QA kuralları. `EP-COLORS-5-V1` birebir korundu → `JOB-EN-eea4cd1f` aynı kalır, **tekrar yüklenmez**.
- `backend/engine/supabase_rest.py` (yeni): tüm Supabase REST çağrıları tek yerde.
- `production_runner.py` yeniden yazıldı: idempotency kontrolü, her aşamada `pipeline_jobs.state` + heartbeat, hata durumları (`FAILED_QA / FAILED_UPLOAD / QUOTA_PAUSED / QUARANTINED`), 5xx için 3 deneme, kota tespiti, dile özel `YOUTUBE_REFRESH_TOKEN_<DİL>`, drawtext kaçış sorunlarını önleyen textfile, 45 sn altına düşmemek için 2–4 sn etkileşim duraklaması, `--dry-run`.
- `factory_orchestrator.py` yeniden yazıldı: `enabled` → `schedule_time`(saat dilimi) → günlük hedef → dil bazlı hata/kota duraklatma → sıradaki **yeni** bölüm. İçerik biterse `CONTENT_EXHAUSTED` (kopya yok). Her işten ve yüklemeden önce `enabled` tekrar okunur (STOP telefon kapalıyken de çalışır). `last_run_at / next_run_at / failure_count` güncellenir.
- `backend/tests/test_factory_logic.py`: 16 birim testi (zamanlama, günlük limit, kota, dil izolasyonu, idempotency, müfredat QA).

**Workflow'lar**
- `smartkids_factory.yml`: tek üretim giriş noktası. Ucuz `gate` işi her saat (:17) heartbeat yazar ve karar verir; ağır ARM64 `produce` işi yalnızca iş varsa çalışır. `run_now` girdisi = Android START.
- `production_pipeline.yml`: manuel tek iş/debug aracı; `dry_run` girdisi, doğrulama adımı artık girilen bölüm/dili kontrol ediyor, fabrika ile aynı concurrency grubunda.
- `android_build.yml` (yeni): her push'ta uygulamayı derler + JVM testlerini çalıştırır (APK yayınlamaz).

**Android**
- START: önce Supabase `enabled=true` (başarısızsa durum değişmez ve hata gösterilir), sonra `smartkids_factory.yml` `run_now=true`. Sahte yerel iş yok.
- Supabase `pipeline_jobs` artık yerel tabloyu **tamamen değiştirir** (sahte/eski satırlar temizlenir); `updated_at` gerçek zaman.
- Durum eşlemesi backend adlarına göre; 2 saatten eski "yarım" iş aktif sayılmaz; heartbeat 2 saatten eskiyse uyarı.
- Sahte demo işler ve "Aşamayı İlerlet" sahte geçişleri kaldırıldı; zamanlama Supabase'e yazılıyor.

**Supabase (opsiyonel)**: `backend/database/supabase_rls_hardening.sql` — Android anon anahtarı yalnızca okuma + 5 kontrol kolonunu güncelleme.

## 3. Doğrulama (bu oturumda)
- 16/16 birim testi geçti.
- 8 bölümün tamamı x86 üzerinde `--dry-run` ile render edildi: hepsi 1920×1080 h264/aac, 47–53 sn, teknik QA PASS. (HuggingFace bu ortamdan erişilemediği için ses Piper yerine süre-eşdeğer test tonu ile üretildi; tahmini süreler gerçek Piper sürelerine ±0,3 sn yakın.)
- **Doğrulanmadı:** Android derlemesi (bu ortamda Android SDK/Maven erişimi yok → `android_build.yml` bunu GitHub'da yapacak), gerçek Supabase/YouTube çağrıları (secret'lar yalnızca GitHub'da).

## 4. Senin yapman gerekenler
1. `docs/workflows_to_copy/` içindeki 3 dosyayı `.github/workflows/` içine kopyala (üzerine yaz) — bu klasöre uzaktan yazılamıyor.
2. Değişiklikleri GitHub `main`'e push et (GitHub Desktop ile `D:\ClaudeProje\smartkids-network` → commit → push, veya web'den yükle).
3. Actions → *Android Control Center build check* yeşil mi? Kırmızıysa log'u bana gönder.
4. Actions → *SmartKids Production Pipeline* → `EP-NUMBERS-1-5-V1`, `EN`, `dry_run=true` → gerçek Piper ile render testi.
5. Aynı iş `dry_run=false` → ikinci gerçek video (private). Ardından `EP-COLORS-5-V1` ile çalıştır: **"already on YouTube — no re-upload"** görmelisin (idempotency kanıtı).
6. Telefonda yeni APK → START → Actions'ta *Cloud Autonomous Factory* `run_now=true` ile başlamalı, uygulamada aşamalar TTS → RENDER → UPLOAD olarak ilerlemeli.
7. GitHub PAT'i yalnızca bu repo + "Actions: read/write" yetkili, süreli fine-grained token yap.

## 5. Bilinmesi gereken dış kısıtlar
- **Public yayın:** YouTube, 28 Temmuz 2020 sonrası oluşturulmuş ve denetimden (audit) geçmemiş API projelerinden `videos.insert` ile yüklenen videoları *private* ile sınırlar. Otomatik public yayın için Google'ın YouTube API Compliance Audit başvurusu gerekir.
- **Cron:** Public repolarda 60 gün commit olmazsa GitHub zamanlanmış workflow'ları kapatır. Heartbeat 2 saatten eskiyse uygulama uyarır.
- **İçerik:** 8 bölüm ≈ 8 günlük EN üretim. Sonra fabrika `CONTENT_EXHAUSTED` ile durur (kopya üretmez). Sıradaki iş: Gemini free tier ile yeni bölüm üretimi + QA.

## 6. Tamamlanma tahmini

| Alan | Ağırlık | Durum | Katkı |
|---|---|---|---|
| Bulut üretim çekirdeği (TTS, render, QA, upload, kayıt) | 20 | %85 | 17 |
| Otonom zamanlama / idempotency / kota / izolasyon | 15 | %60 (kod hazır, canlı test yok) | 9 |
| Android kumanda | 10 | %65 (cihaz testi yok) | 6.5 |
| İçerik zekâsı (konu keşfi, müfredat, senaryo) | 15 | %25 | 3.75 |
| Görsel üretim | 10 | %15 | 1.5 |
| Çok dil (10 dil) | 10 | %10 (yalnız EN) | 1 |
| SEO | 5 | %50 | 2.5 |
| Public yayın | 5 | %10 (audit gerekli) | 0.5 |
| Analytics + öğrenme döngüsü | 5 | %5 | 0.25 |
| Hukuk/lisans QA | 5 | %30 | 1.5 |
| **Toplam** | 100 | | **≈ %43** |

Bu düzeltmelerden önce ≈ %35 idi (otonom döngü kopya üretecek durumdaydı). "1 dil × günlük 1 video, private" hedefi için ≈ %80.
