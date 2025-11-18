import os
import socket
from yt_dlp import YoutubeDL


def sanitize_for_fs(name: str) -> str:
    """Basit dosya sistemi güvenli ad üretimi."""
    invalid_chars = '<>:"/\\|?*'
    cleaned = "".join(c for c in name if c not in invalid_chars)
    cleaned = cleaned.strip().replace(" ", "_")
    return cleaned or "playlist"


def describe_error(ex: Exception) -> str:
    """Hataları kullanıcı için daha anlaşılır kategorilere ayır."""
    msg = str(ex) if ex else ""
    lower = msg.lower()

    # İnternet / bağlantı
    if isinstance(ex, (socket.gaierror, ConnectionError, TimeoutError)) or any(
        k in lower for k in ["timed out", "connection reset", "name or service not known", "network is unreachable"]
    ):
        return "İnternet veya bağlantı hatası. Lütfen bağlantınızı kontrol edin ve tekrar deneyin."

    # ffmpeg bulunamadı / çalıştırılamadı
    if "ffmpeg" in lower and any(k in lower for k in ["not found", "is not recognized", "no such file"]):
        return "FFmpeg bulunamadı. Lütfen ffmpeg'in sisteminizde kurulu ve PATH içinde olduğundan emin olun."

    # Disk / izin
    if isinstance(ex, PermissionError) or "permission denied" in lower:
        return "Dosya yazma izni yok. Uygulamayı yeterli yetki ile çalıştırın veya çıktı klasörünüzün izinlerini kontrol edin."

    if isinstance(ex, OSError) and any(k in lower for k in ["no space left on device", "disk full"]):
        return "Disk dolu. Lütfen biraz yer açıp tekrar deneyin."

    # yt-dlp / YouTube spesifik
    if "yt-dlp" in lower or "youtube" in lower or "video unavailable" in lower:
        return "YouTube/yt-dlp kaynaklı bir hata oluştu. Video kısıtlı veya geçici bir sorun olabilir. Bir süre sonra tekrar deneyin."

    # Varsayılan
    return f"Beklenmeyen bir hata oluştu: {msg}"


def fetch_playlist_info(playlist_url, verbose: bool = False):
    """Return a dict: {'title': playlist_title, 'entries': [{'id':..., 'title':..., 'url':...}, ...]}"""
    ydl_opts = {
        "quiet": True,
        # playlist bilgilerini indirir, video dosyalarını indirmez
        "skip_download": True,
        "ignoreerrors": True,
        "noplaylist": False,
        # tam playlist bilgisini al (entries listesi dolsun)
        # "extract_flat" kullanmıyoruz ki yt-dlp playlist'i tam açsın
    }
    with YoutubeDL(ydl_opts) as ydl:
        if verbose:
            print("[downloader] Fetching playlist info:", playlist_url)
        info = ydl.extract_info(playlist_url, download=False)

    entries = []
    if info is None:
        return {"title": "", "entries": entries}

    playlist_title = info.get("title") or "Oynatma listesi"
    raw_entries = info.get("entries") or [info]
    for e in raw_entries:
        if not e:
            continue
        video_id = e.get("id")
        title = e.get("title") or video_id
        if video_id:
            url = f"https://www.youtube.com/watch?v={video_id}"
        else:
            url = e.get("webpage_url") or e.get("url") or ""
        entries.append({"id": video_id, "title": title, "url": url})
    return {"title": playlist_title, "entries": entries}


def download_as_mp3(url, output_dir, progress_callback=None, verbose: bool = False):
    """Download single youtube video and convert to mp3 using yt-dlp + ffmpeg.

    progress_callback(percent, status_text) is optional.
    Returns filepath on success, raises on error.
    """
    outtmpl = os.path.join(output_dir, "%(id)s_%(title)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    def _hook(d):
        if progress_callback:
            status = d.get("status")
            if status == "downloading":
                percent = d.get("_percent_str") or d.get("percent")
                progress_callback(percent, "downloading")
            elif status == "finished":
                progress_callback("100.0", "converting")
            elif status == "error":
                progress_callback("0", "error")

    ydl_opts["progress_hooks"] = [_hook]

    with YoutubeDL(ydl_opts) as ydl:
        if verbose:
            print("[downloader] Downloading:", url)
        info = ydl.extract_info(url, download=True)

    title = info.get("title", "unknown")
    vid_id = info.get("id", "")
    if vid_id:
        filename = f"{vid_id}_{title}.mp3"
    else:
        filename = f"{title}.mp3"
    filepath = os.path.join(output_dir, filename)

    if os.path.exists(filepath):
        return filepath

    id_prefix = (vid_id or "")
    title_prefix = (title or "")[:8].lower()
    for f in os.listdir(output_dir):
        if not f.lower().endswith(".mp3"):
            continue
        lower = f.lower()
        if id_prefix and lower.startswith(id_prefix.lower() + "_"):
            return os.path.join(output_dir, f)
        if not id_prefix and title_prefix and title_prefix in lower:
            return os.path.join(output_dir, f)

    raise FileNotFoundError("MP3 file not found after conversion.")
