# app.py
# Python 3.12
# Flet GUI + yt-dlp backend to download YouTube playlist videos as mp3 files.
# Usage: python app.py
import threading
import os
import tempfile
import traceback
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
import flet as ft
from config import OUTPUT_DIR, DEFAULT_MAX_WORKERS, MAX_RETRIES, VERBOSE_LOGGING
from downloader import fetch_playlist_info, download_as_mp3, sanitize_for_fs, describe_error


def main(page: ft.Page):
    page.title = "YouTube Playlist → MP3 (Flet + yt-dlp)"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.window_width = 900
    page.window_height = 700
    page.theme_mode = ft.ThemeMode.LIGHT

    page.bgcolor = ft.Colors.GREY_50

    lbl_status = ft.Text("", size=13, weight=ft.FontWeight.W_500)
    lbl_playlist_info = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    txt_playlist = ft.TextField(label="YouTube playlist URL veya paylaşım linki", width=700)
    btn_fetch = ft.ElevatedButton("Listeyi Getir", icon=ft.Icons.LIST, disabled=False)

    list_view = ft.ListView(expand=True, spacing=5, padding=10)
    chk_all = ft.Checkbox(label="Tümünü seç", value=False)

    btn_download_selected = ft.ElevatedButton("Seçileni MP3 indir", icon=ft.Icons.DOWNLOAD, disabled=True)
    btn_download_all = ft.ElevatedButton("Hepsini MP3 indir", icon=ft.Icons.DOWNLOAD, disabled=True)
    btn_cancel = ft.TextButton("İptal", icon=ft.Icons.CANCEL, disabled=True)
    ddl_max_workers = ft.Dropdown(
        label="Paralel indirme sayısı",
        width=180,
        value=str(DEFAULT_MAX_WORKERS),
        options=[ft.dropdown.Option(str(i)) for i in range(1, 6)],
    )

    txt_max_retries = ft.TextField(
        label="Maksimum tekrar (retry)",
        width=160,
        value=str(MAX_RETRIES),
    )
    sw_verbose = ft.Switch(label="Ayrıntılı log (konsola)", value=VERBOSE_LOGGING)
    btn_reset_defaults = ft.TextButton("Varsayılanları geri yükle", icon=ft.Icons.RESTORE)

    progress_bar = ft.ProgressBar(width=700, visible=False)
    progress_text = ft.Text("")
    lbl_failed = ft.Text("", size=12)

    # store entries and checkboxes
    app_state = {
        "entries": [],
        "boxes": [],
        "playlist_title": "",
        "cancel_requested": False,
        "output_dir": OUTPUT_DIR,
        "max_workers": DEFAULT_MAX_WORKERS,
        "max_retries": MAX_RETRIES,
        "verbose_logging": VERBOSE_LOGGING,
        "failed": [],
    }

    def set_status(text, color=None):
        lbl_status.value = text
        if color:
            lbl_status.color = color
        page.update()

    def on_fetch_click(e):
        url = txt_playlist.value.strip()
        if not url:
            set_status("Önce oynatma listesi URL'si girin.", "red")
            return

        set_status("Oynatma listesi alınıyor... lütfen bekleyin.", None)
        btn_fetch.disabled = True
        btn_download_all.disabled = True
        btn_download_selected.disabled = True
        list_view.controls.clear()
        lbl_playlist_info.value = ""
        page.update()

        def worker():
            try:
                result = fetch_playlist_info(url, verbose=app_state.get("verbose_logging", VERBOSE_LOGGING))
                entries = result["entries"]
                playlist_title = result.get("title") or ""
                if not entries:
                    set_status("Oynatma listesi bulunamadı veya boş.", "red")
                    btn_fetch.disabled = False
                    page.update()
                    return
                app_state["entries"] = entries
                app_state["boxes"] = []
                app_state["playlist_title"] = playlist_title
                # playlist için alt klasör oluştur
                safe_title = sanitize_for_fs(playlist_title)
                count = len(entries)
                today_str = date.today().isoformat()
                folder_name = f"{safe_title}_{count}_video_{today_str}"
                playlist_dir = os.path.join(OUTPUT_DIR, folder_name)
                os.makedirs(playlist_dir, exist_ok=True)
                app_state["output_dir"] = playlist_dir
                def build_list():
                    list_view.controls.clear()
                    app_state["boxes"].clear()
                    for idx, ent in enumerate(entries):
                        box = ft.Checkbox(label=f"{idx+1}. {ent['title']} [bekliyor]", value=False)
                        box.label_style = ft.TextStyle(color=ft.Colors.GREY_600)
                        app_state["boxes"].append(box)
                        list_view.controls.append(box)
                    btn_download_all.disabled = False
                    btn_download_selected.disabled = False
                    page.update()
                build_list()
                lbl_playlist_info.value = f"Oynatma listesi: {playlist_title} ({len(entries)} video)"
                set_status(f"{len(entries)} video bulundu.", "green")
            except Exception as ex:
                tb = traceback.format_exc()
                print(tb)
                friendly = describe_error(ex)
                set_status(friendly, "red")
            finally:
                btn_fetch.disabled = False
                page.update()

        threading.Thread(target=worker, daemon=True).start()

    def download_worker(items, single_mode=False):
        """items: list of (orig_index, video_id, title, url)  — paralel indirme + retry"""
        total = len(items)
        if total == 0:
            return

        max_workers = min(app_state.get("max_workers", DEFAULT_MAX_WORKERS), total)
        app_state["cancel_requested"] = False
        app_state["failed"] = []
        progress_bar.visible = True
        progress_bar.value = 0.0
        progress_text.value = ""
        btn_cancel.disabled = False
        page.update()

        completed = 0

        def update_box_label(orig_index, status_tag, color=None):
            try:
                box = app_state["boxes"][orig_index]
                title_part = box.label
                # strip eski köşeli etiket
                if "[" in title_part:
                    title_part = title_part.split("[")[0].strip()
                box.label = f"{title_part} [{status_tag}]"
                # Varsayılan renkleri status_tag'e göre seç
                if color is None:
                    if status_tag == "bekliyor":
                        color = ft.Colors.GREY_600
                    elif status_tag == "indiriliyor":
                        color = ft.Colors.BLUE
                    elif status_tag == "başarılı":
                        color = ft.Colors.GREEN
                    elif status_tag == "tekrar deneniyor":
                        color = ft.Colors.AMBER
                    elif status_tag == "hata":
                        color = ft.Colors.RED
                    elif status_tag == "zaten indirildi":
                        color = ft.Colors.GREEN_700
                if color:
                    box.label_style = ft.TextStyle(color=color)
            except Exception:
                pass

        def download_task(orig_index, display_index, video_id, title, url):
            if app_state["cancel_requested"]:
                return False

            target_dir = app_state.get("output_dir", OUTPUT_DIR)

            # Önce aynı sıra numarasıyla (1., 2., 3. ...) başlayan bir mp3 zaten var mı kontrol et
            try:
                already_exists = False
                order_prefix = f"{display_index + 1}.".lower()
                for f in os.listdir(target_dir):
                    lower = f.lower()
                    if lower.endswith(".mp3") and lower.startswith(order_prefix):
                        already_exists = True
                        break
                if already_exists:
                    update_box_label(orig_index, "zaten indirildi", ft.Colors.GREEN)
                    set_status(f"Atlandı (zaten mevcut): {title}", "green")
                    return True
            except Exception:
                # Eğer burada bir hata olursa normal indirme akışına devam et
                pass

            attempts = 0
            last_error = None

            current_max_retries = app_state.get("max_retries", MAX_RETRIES)

            while attempts < current_max_retries and not app_state["cancel_requested"]:
                attempts += 1
                try:
                    update_box_label(orig_index, "indiriliyor")
                    set_status(f"{display_index + 1}/{total} indiriliyor (deneme {attempts}): {title}")
                    filepath = download_as_mp3(
                        url,
                        target_dir,
                        progress_callback=None,
                        verbose=app_state.get("verbose_logging", VERBOSE_LOGGING),
                        order_index=display_index,
                        title_override=title,
                    )
                    update_box_label(orig_index, "başarılı", ft.Colors.GREEN)
                    set_status(f"Tamamlandı: {os.path.basename(filepath)}", "green")
                    return True
                except Exception as ex:
                    last_error = ex
                    if app_state.get("verbose_logging", VERBOSE_LOGGING):
                        print("Download error:", ex)
                    if attempts < current_max_retries:
                        update_box_label(orig_index, "tekrar deneniyor", ft.Colors.RED)
                        friendly = describe_error(ex)
                        set_status(
                            f"İndirme hatası, tekrar denenecek (deneme {attempts}): {title}\n{friendly}",
                            "red",
                        )
                    else:
                        update_box_label(orig_index, "hata", ft.Colors.RED)
                        friendly = describe_error(ex)
                        set_status(
                            f"İndirme başarısız ({attempts} deneme): {title}\n{friendly}",
                            "red",
                        )
                        app_state["failed"].append((orig_index, title, ex))
            return False

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {
                executor.submit(download_task, orig_idx, idx, video_id, title, url): (orig_idx, video_id, title, url)
                for idx, (orig_idx, video_id, title, url) in enumerate(items)
            }

            for future in as_completed(future_to_item):
                if app_state["cancel_requested"]:
                    set_status("İndirme iptal edildi.", "red")
                    break

                _orig_idx, _vid, _title, _url = future_to_item[future]
                try:
                    _ = future.result()
                except Exception as ex:
                    if app_state.get("verbose_logging", VERBOSE_LOGGING):
                        print("Unexpected worker error:", ex)

                completed += 1
                progress_bar.value = completed / total
                progress_text.value = f"{completed}/{total} tamamlandı"
                page.update()

        btn_cancel.disabled = True
        progress_bar.visible = False
        app_state["cancel_requested"] = False
        target_dir = app_state.get("output_dir", OUTPUT_DIR)

        if app_state["failed"]:
            failed_titles = [title for (_i, title, _e) in app_state["failed"]]
            summary = f"{len(failed_titles)} videoda hata oluştu:\n" + "\n".join(
                f"- {t}" for t in failed_titles
            )
            lbl_failed.value = summary
        else:
            lbl_failed.value = ""

        set_status(f"İndirme işlemi bitti. Dosyalar: {target_dir}", "green")
        page.update()

    def on_download_selected(e):
        # collect checked
        checked = []
        for idx, (box, ent) in enumerate(zip(app_state["boxes"], app_state["entries"])):
            if box.value:
                checked.append((idx, ent.get("id"), ent["title"], ent["url"]))
        if not checked:
            set_status("Seçili video yok.", "red")
            return
        btn_download_selected.disabled = True
        btn_download_all.disabled = True
        page.update()
        def run_download_selected():
            download_worker(checked)
            btn_download_selected.disabled = False
            btn_download_all.disabled = False
            page.update()

        threading.Thread(target=run_download_selected, daemon=True).start()

    def on_download_all(e):
        entries = [
            (idx, ent.get("id"), ent["title"], ent["url"])
            for idx, ent in enumerate(app_state["entries"])
        ]
        if not entries:
            set_status("İndirilecek video yok.", "red")
            return
        btn_download_selected.disabled = True
        btn_download_all.disabled = True
        page.update()
        def run_download_all():
            download_worker(entries)
            btn_download_selected.disabled = False
            btn_download_all.disabled = False
            page.update()

        threading.Thread(target=run_download_all, daemon=True).start()

    def on_check_all(e):
        for b in app_state["boxes"]:
            b.value = chk_all.value
        page.update()

    def on_max_workers_change(e):
        try:
            app_state["max_workers"] = int(e.control.value)
        except Exception:
            app_state["max_workers"] = DEFAULT_MAX_WORKERS
        page.update()

    def on_max_retries_change(e):
        try:
            value = int(e.control.value)
            if value < 1:
                value = 1
            if value > 10:
                value = 10
            app_state["max_retries"] = value
            txt_max_retries.value = str(value)
        except Exception:
            app_state["max_retries"] = MAX_RETRIES
            txt_max_retries.value = str(MAX_RETRIES)
        page.update()

    def on_verbose_toggle(e):
        app_state["verbose_logging"] = bool(e.control.value)
        page.update()

    def on_cancel(e):
        app_state["cancel_requested"] = True
        set_status("İptal isteği gönderildi, mevcut indirme tamamlandıktan sonra duracak.", "red")
        page.update()

    def on_reset_defaults(e):
        app_state["max_workers"] = DEFAULT_MAX_WORKERS
        app_state["max_retries"] = MAX_RETRIES
        app_state["verbose_logging"] = VERBOSE_LOGGING

        ddl_max_workers.value = str(DEFAULT_MAX_WORKERS)
        txt_max_retries.value = str(MAX_RETRIES)
        sw_verbose.value = VERBOSE_LOGGING
        page.update()

    # Wire events
    btn_fetch.on_click = on_fetch_click
    btn_download_selected.on_click = on_download_selected
    btn_download_all.on_click = on_download_all
    chk_all.on_change = on_check_all
    btn_cancel.on_click = on_cancel
    ddl_max_workers.on_change = on_max_workers_change
    txt_max_retries.on_change = on_max_retries_change
    sw_verbose.on_change = on_verbose_toggle
    btn_reset_defaults.on_click = on_reset_defaults

    # Layout
    controls = [
        ft.Container(
            content=ft.Column(
                [
                    ft.Row([txt_playlist, btn_fetch]),
                    lbl_playlist_info,
                    ft.Row([chk_all, btn_download_selected, btn_download_all, btn_cancel, ddl_max_workers]),
                    ft.Text("Ayarlar:", size=14, weight=ft.FontWeight.BOLD),
                    ft.Row([txt_max_retries, sw_verbose, btn_reset_defaults]),
                    ft.Text("Videolar:", size=16),
                    ft.Container(
                        content=list_view,
                        height=360,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        padding=10,
                        bgcolor=ft.Colors.WHITE,
                    ),
                    progress_bar,
                    progress_text,
                    lbl_failed,
                    ft.Container(
                        content=lbl_status,
                        padding=10,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        bgcolor=ft.Colors.WHITE,
                    ),
                    ft.Text(f"Ana çıktı klasörü: {OUTPUT_DIR}", size=12),
                ],
                spacing=10,
            ),
            padding=15,
        )
    ]
    page.add(*controls)


if __name__ == "__main__":
    ft.app(target=main, view=ft.WEB_BROWSER)
