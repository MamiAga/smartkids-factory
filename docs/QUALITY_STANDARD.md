# SKQS-3 — SmartKids Video Kalite Standardı (v3: Oyunculuk Kuralı)

Kural: **Tek bir madde geçmezse video YouTube'a yüklenmez** (iş `FAILED_QA`, fabrika sıradaki bölüme geçer).
Ölçümler son MP4 üzerinde yapılır (`backend/engine/quality.py`); rapor her işte `<job_id>_quality_report.json` olarak artifact'a konur.

## 1. Format ve süre
| Kural | Eşik |
|---|---|
| Süre | **8:15 – 10:30** (495–630 sn; mid-roll reklam uygun). Kısa kalırsa otomatik "Bonus round" eklenir |
| Görüntü | 1920×1080, tam 60 fps, H.264 High, yuv420p, CRF 18, BT.709 |
| Ses | AAC 48 kHz stereo 192 kbps |

## 2. Ses ve seslendirme
| Kural | Eşik |
|---|---|
| Anlatıcı | Kokoro-82M `af_heart` (kadın, sıcak, hikâye anlatıcı tonu; Apache-2.0). Robotik ses yedeği **yok** — model yüklenemezse iş durur |
| Konuşma hızı | 90–150 kelime/dk (ölçülür) |
| Sıfır sessizlik | Kesintisiz neşeli müzik yatağı; 1 sn'den uzun sessizlik = FAIL (`silencedetect -45 dB`) |
| Müzik | SmartKids'in kendi ürettiği özgün müzik (lisans riski yok), Lumi konuşurken −10 dB otomatik kısılır |
| Ses yüksekliği | −16 LUFS ±1, true peak ≤ −1 dBTP |
| Efektler | Sahne çanı, geri sayım tik'i, doğru cevap "tada" |

## 3. Görsel
| Kural | Eşik |
|---|---|
| Her segmentte resim | emoji çizim (Noto, Apache-2.0) |
| Maskot | Lumi her karede, hafif hareketli |
| Süsleme | Her karede çiçek ve böcek süsleri |
| Okunabilirlik | Yazı kontrastı ≥ 4,5:1, yazı ≥ 48 px |
| Flash guard | Kareden kareye parlaklık değişimi ≤ 12/255; renk değişen geçişlerde 0,3 sn yumuşak geçiş |
| Siyah ekran | > 0,5 sn yok |

## 4. İnteraktif aktivite formatı
- Her öğeden önce **"Tahmin et!" + 3-2-1 geri sayım**.
- Her öğe: tanıtım → "benimle söyle" → 3 örnek → **"Hangisi?" quiz + 3-2-1 geri sayım** → cevap.
- Ortada dans molası, sonda tahmin turu (her soruda geri sayım), birlikte söyleme ve kapanış.
- Geri sayım sayısı ≥ öğe sayısı (ölçülür).

## 5. Metadata
- Başlık formülü: **Eğlence kelimesi + ebeveyn arama terimi**, ör. *"Colors Dance Party! 🍓 Learn Colors for Toddlers & Preschoolers | SmartKids"*.
- Açıklamada bölümler (chapters, 0:00'dan başlar), öğrenme hedefi, ebeveyn/öğretmen notu, lisans atıfları.
- `selfDeclaredMadeForKids = true` (zorunlu, standart dışı bırakılamaz).
- 1280×720 kapak: gökkuşağı, çiçek/böcek, maskot.

## 6. Yayın
Kalite kapısı geçti → private yükleme → YouTube işlemesi bitti → `publish_mode` (AUTO = public).
API denetimi onaylanana kadar YouTube videoyu private'ta tutar; sistem bunu `PUBLISH_BLOCKED_BY_YOUTUBE` olarak kaydeder.

## 7. Oyunculuk kuralı (SKQS-3)
| Kural | Eşik (ölçülür) |
|---|---|
| Nida | Satırların ≥ %80'i "Wow / Oh / Ooh / Yay / Oh-oh / Look / Hooray / Woo-hoo / Whee" ile başlar (şarkı kelimeleri hariç) |
| Duygu etiketi | Satırların ≥ %95'i `[excited]` / `[whisper]` / `[calm]` etiketli. Excited = hızlı ve tam ses, whisper = yavaş ve çok kısık |
| Dinamik | En az 5 fısıltı satırı (hep bağıran bir ses de monotondur) |
| Geri sayım | Lumi "Three! Two! One!" der; altında tik-tak saat sesi; sonunda "go" zili |
| Belirme efekti | Nesne ekrana zıplayarak düşer; sırayla tada / boing / çan / ördek vaklaması / pop |
| Müzik | 124 BPM, Lumi konuşurken %70 kısılır, bitince geri yükselir |
| Konuşma hızı | 90–160 kelime/dk |

Not: Kokoro SSML/duygu etiketi desteklemez. `[excited]` gibi etiketler motor tarafından tempo + ses seviyesi + cümle arası nefes olarak uygulanır;
heyecanı asıl taşıyan nidalar ve ünlem noktalamasıdır. Gerçek "gülme" sesi üretilemediği için `[laughing]` kullanılmaz.
Her işte sahne-sahne ses planı `<job_id>_scenes.json` olarak dışa aktarılır (scene_id, duration_sec, background_music, sfx_at_start, text_to_speech).
