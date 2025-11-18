# YouTube Playlist → MP3 (Flet + yt-dlp)

Bu proje, YouTube oynatma listelerini (playlist) masaüstünde çalışan bir **Flet** arayüzü üzerinden **MP3** dosyaları olarak indirmek için tasarlanmıştır. Arkaplanda **yt-dlp** ve **FFmpeg** kullanılır.

- Playlist URL’si girersin.
- Uygulama listeyi çözümler, videoları listeler.
- İstersen tümünü, istersen sadece seçtiklerini MP3 olarak indirirsin.
- İndirme işlemi paralel (çoklu) ve her video için otomatik yeniden deneme (retry) içerir.
- Daha önce indirilmiş videoları video ID’sine göre tespit edip tekrar indirmez.
- Hatalar kullanıcı dostu mesajlarla ve durum etiketleriyle gösterilir.

---

## Proje yapısı

Klasör (özet):

- `app.py`
  - Flet ile yazılmış ana GUI uygulaması.
  - Playlist URL girişi, video listesi, seçim checkbox’ları.
  - `Seçileni indir`, `Hepsini indir`, `İptal` butonları.
  - Global progress bar ve ayrıntılı durum/hata mesajları.
  - `Ayarlar` bölümü (max paralel indirme, max retry, verbose log, varsayılanları geri yükle).
- `downloader.py`
  - yt-dlp + FFmpeg tabanlı indirme ve playlist çözme fonksiyonları.
  - `fetch_playlist_info(playlist_url, verbose=False)`
  - `download_as_mp3(url, output_dir, progress_callback=None, verbose=False)`
  - `sanitize_for_fs(name)` – klasör/dosya isimlerini dosya sistemi için temizler.
  - `describe_error(ex)` – internet, ffmpeg, disk, izin, YouTube/yt-dlp vb. hataları sınıflandırıp anlamlı Türkçe mesaj üretir.
- `config.py`
  - Proje genelinde kullanılan konfigürasyon sabitleri:
    - `OUTPUT_DIR` – ana çıktı klasörü (`./downloads`).
    - `DEFAULT_MAX_WORKERS` – varsayılan paralel indirme sayısı.
    - `MAX_RETRIES` – her video için maksimum yeniden deneme sayısı.
    - `VERBOSE_LOGGING` – ayrıntılı logların konsola yazılıp yazılmayacağı (başlangıç değeri).

İndirme sırasında:

- Playlist başlığına göre, içinde tarih ve video sayısı olan bir alt klasör açılır:
  - Örn: `downloads/playlist_adi_25_video_2025-11-18`
- Her video şu formatta saklanır:
  - `videoId_title.mp3`

---

## Başlıca özellikler

- **Playlist çözme:**
  - `fetch_playlist_info` ile yt-dlp kullanılarak playlist başlığı ve videoların listesi alınır.
  - Her video için `id`, `title`, `url` alanları belirlenir.

- **Paralel indirme:**
  - `ThreadPoolExecutor` ile birden fazla video aynı anda indirilebilir.
  - UI’de `Paralel indirme sayısı` dropdown’ı (1–5) ile ayarlanabilir.

- **Retry (yeniden deneme) desteği:**
  - Her video için `max_retries` kadar (varsayılan `MAX_RETRIES`) yeniden deneme yapılır.
  - Hata durumunda "tekrar deneniyor" etiketi ve ayrıntılı hata mesajı gösterilir.

- **Zaten indirilenleri atlama:**
  - Playlist klasöründe video ID’si ile başlayan bir `.mp3` dosyası varsa video "zaten indirildi" kabul edilir, indirilmez.

- **Durum etiketleri:**
  - Her video satırında bir durum etiketi ve renk kodu bulunur:
    - `[bekliyor]` – gri
    - `[indiriliyor]` – mavi
    - `[başarılı]` – yeşil
    - `[tekrar deneniyor]` – turuncu
    - `[hata]` – kırmızı
    - `[zaten indirildi]` – koyu yeşil

- **Ayarlar paneli:**
  - `Maksimum tekrar (retry)` – 1–10 arası integer; çalışma anında değiştirilebilir.
  - `Ayrıntılı log (konsola)` – `Switch`; indirme ve playlist loglarının (yt-dlp çağrıları, hatalar) konsola yazılıp yazılmasını kontrol eder.
  - `Varsayılanları geri yükle` – `config.py`’deki `DEFAULT_MAX_WORKERS`, `MAX_RETRIES`, `VERBOSE_LOGGING` değerlerine geri döner.

- **Detaylı hata mesajları:**
  - İnternet/bağlantı hataları.
  - FFmpeg bulunamadı / PATH’te değil.
  - Disk dolu.
  - Dosya izin hataları.
  - YouTube/yt-dlp ile ilgili kısıt/erişim sorunları.

---

## Gereksinimler

- **Python**: 3.11+ (proje yorumlarında 3.12 belirtilmiş, 3.11 ile de çalışır).
- **pip**: Python paket yöneticisi.
- **FFmpeg**: Sisteminizde kurulu ve PATH içinde olmalı.
  - macOS (Homebrew ile):
    ```bash
    brew install ffmpeg
    ```
  - Debian/Ubuntu:
    ```bash
    sudo apt update
    sudo apt install ffmpeg
    ```
  - Windows:
    - https://ffmpeg.org dan binary indirip PATH’e ekleyin.

- **Python kütüphaneleri:**
  - `flet`
  - `yt-dlp`

Projeyle beraber bir `requirements.txt` yoksa aşağıdaki gibi oluşturabilirsiniz:

```txt
flet
yt-dlp
```

---

## Kurulum

1. Depoyu/klasörü bilgisayarınıza alın:
   ```bash
   cd /path/to/youtube_oynatma_listesi_mp3_olarak_indirme
   ```

2. Sanal ortam (opsiyonel ama tavsiye edilir):
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
   ```

3. Python bağımlılıklarını yükleyin:
   ```bash
   pip install flet yt-dlp
   ```

4. FFmpeg’i sisteminize kurun (yukarıdaki talimatlara göre).

5. FFmpeg’i test edin:
   ```bash
   ffmpeg -version
   ```

---

## Çalıştırma

Flet uygulamasını başlatmak için:

```bash
flet run app.py
```

veya

```bash
python app.py
```

Bu komut, varsayılan olarak tarayıcıda veya Flet’in kendi penceresinde UI’yi açacaktır.

---

## Kullanım

1. **Playlist URL’sini girin**
   - Örn: YouTube playlist linki veya paylaşım linki.

2. **"Listeyi Getir" butonuna tıklayın**
   - Uygulama:
     - yt-dlp ile playlist bilgilerini çeker.
     - Videoları listeler (1., 2., 3. ...).
     - Her satırda checkbox ve `[bekliyor]` etiketi görünür.
     - Playlist başlığına göre `downloads/` altında bir alt klasör oluşturur.

3. **Videoları seçin**
   - `Tümünü seç` ile hepsini işaretleyebilir veya sadece bazılarını seçebilirsiniz.

4. **İndirme başlatın**
   - `Seçileni MP3 indir` veya `Hepsini MP3 indir` butonu.
   - İndirme sırasında:
     - Etiketler duruma göre güncellenir.
     - Global progress bar toplam tamamlanan video sayısına göre ilerler.
     - Hata durumunda hem etiket rengi hem de alt kısımdaki hata mesajı güncellenir.

5. **İptal**
   - `İptal` butonu, mevcut çalışan indirmeler bittikten sonra kuyruğu durdurur.

6. **Ayarlar**
   - `Maksimum tekrar (retry)` alanını değiştirerek indirme başına deneme sayısını ayarlayabilirsiniz.
   - `Ayrıntılı log (konsola)` switch’i ile konsol loglarını açıp kapayabilirsiniz.
   - `Varsayılanları geri yükle` ile tüm ayarları `config.py` içindeki başlangıç değerlerine geri alabilirsiniz.

---

## Bilinen kısıtlar ve notlar

- **Android / mobil:**
  - Bu proje masaüstü (ve web) için tasarlanmıştır. ffmpeg ve yt-dlp, sistem binary’leri olarak çalışır.
  - Tamamen offline, Android APK içine gömülü ffmpeg + yt-dlp çözümü ayrı bir mimari ve ek teknoloji gerektirir.

- **YouTube tarafı uyarıları:**
  - `No supported JavaScript runtime could be found` veya SABR ile ilgili uyarılar yt-dlp kaynaklıdır.
  - Gerekirse yt-dlp’nin önerdiği `--extractor-args` ayarları ileride konfigüre edilebilir.

- **Legal / kullanım:**
  - YouTube içeriklerini indirirken YouTube’un kullanım koşullarını ve telif haklarını göz önünde bulundurun.

---

## Geliştirme için notlar

- Tüm indirme/retry/backoff mantığı `app.py` içindeki `download_worker` fonksiyonunda yönetilir.
- Arka plan işler için `threading.Thread` ve `ThreadPoolExecutor` kullanılır; UI güncellemesi her zaman Flet `page` nesnesi üzerinden yapılır.
- Yeni özellikler eklerken:
  - Backend mantığını mümkün olduğunca `downloader.py` tarafında tutmak,
  - UI ve state yönetimini `app.py` tarafında tutmak,
  - Sabitleri `config.py` üzerinden yönetmek iyi bir ayrım sağlar.
