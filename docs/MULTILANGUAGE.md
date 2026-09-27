# 10 dil + yayın modeli + paralel seslendirme (2026-09-28)

## Ne değişti
| Konu | Önce | Şimdi |
|---|---|---|
| Robot ses | Hızlı satırlar Rubber Band ile yavaşlatılıyordu, temiz çekim bulunamayan satırlar farklı bir motorla (Kokoro) okunuyordu → video içinde ses bir anda robotlaşıp geri dönüyordu | Zaman germe yok, motor karıştırma yok. Her çekim tını/perde/metin kalkanından geçer (docs/QUALITY_STANDARD.md §8) |
| Seslendirme süresi | ~2 saat, tek sunucu | Dil başına 8 ücretsiz GitHub sunucusu aynı anda (ayarlanabilir 1–20) |
| Dil | Yalnız EN | EN ES PT FR DE IT TR RU AR HI |

## Yayın modeli (uygulamadan seçilir: Fabrika Kumandası → Yayın Modeli)
| Mod | Nasıl | İnsan müdahalesi |
|---|---|---|
| `MULTI_CHANNEL` | Her dil kendi kanalına, kendi başlık/yazılarıyla ayrı video | Yok. Her kanal için bir kez OAuth: GitHub Secret `YOUTUBE_REFRESH_TOKEN_<DİL>` |
| `SINGLE_CHANNEL` | Tek kanal (EN), her dil ayrı video | Yok |
| `SINGLE_CHANNEL_MULTI_AUDIO` | Tek video (ekran yazısı EN) + 9 dublaj ses dosyası aynı zaman çizelgesinde; başlık/açıklama çevirileri API ile eklenir | **Var:** YouTube Data API'de ses kanalı yükleme uç noktası yok. Ses dosyaları iş artifact'ında (`*_audio_<DİL>.m4a`); Studio → Diller → Dil ekle → Dublaj. Kanalda "Advanced features" gerekir |

Kanalı bağlı olmayan dil plan aşamasında `LANGUAGE_PAUSED` olur; diğer diller devam eder.

## Kurulum (bir kez)
1. Supabase SQL editöründe `backend/database/2026-09-28_multilanguage.sql` çalıştır (yeni ayar sütunları, yeni iş durumları, 10 dil ses kaydı).
2. `MULTI_CHANNEL` için her dil kanalına `backend/tools/youtube_oauth_helper.py` ile refresh token al → GitHub Secrets `YOUTUBE_REFRESH_TOKEN_ES`, `..._TR` vb.
3. Uygulamada dilleri aç. Önerilen sıra: önce tek dil test üretimi ("Test Üretimi Başlat", "Sadece video üret" işaretli), dinle, sonra aç.

## Paralel seslendirme nasıl çalışır
`factory_core.yml`: **plan** (hangi video, hangi dil, satırlar kaça bölünecek) → **narrate** (matrix: dil × sunucu; her sunucu satırların 1/N'ini seslendirir, sonucu içerik-özetli önbelleğe yazar) → **produce** (tüm parçaları toplar, render + SKQS-4 + YouTube). Aynı satır ikinci kez seslendirilmez (önbellek). STOP: `enabled=false` + çalışan GitHub işleri iptal edilir.
