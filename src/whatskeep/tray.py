"""System tray application for WhatsKeep — no terminal required."""

from __future__ import annotations

import platform
import subprocess
import sys
import threading
from pathlib import Path

from loguru import logger


def _get_icon_image():
    """Load the tray icon as a PIL Image."""
    from PIL import Image

    # Try bundled asset first (PyInstaller), then source tree
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "assets" / "icon-64.png")
    candidates.extend([
        Path(__file__).parent.parent.parent / "assets" / "icon-64.png",
        Path(__file__).parent.parent.parent / "docs" / "icon.svg",
    ])
    for p in candidates:
        if p.exists():
            return Image.open(p)

    # Fallback: generate a simple green circle
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill=(16, 185, 129, 255))
    draw.text((20, 18), "W", fill="white")
    return img


def _open_folder():
    """Open the WhatsKeep backup folder in the file manager."""
    from whatskeep.config import load_config, resolve_backup_dir

    config = load_config()
    backup_dir = resolve_backup_dir(config)
    backup_dir.mkdir(parents=True, exist_ok=True)

    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", str(backup_dir)])
        elif system == "Windows":
            subprocess.Popen(["explorer", str(backup_dir)])
        else:
            subprocess.Popen(["xdg-open", str(backup_dir)])
    except FileNotFoundError:
        logger.warning(f"Could not open folder: {backup_dir}")


def _run_organize():
    """Run one organization pass in a background thread."""

    def _work():
        try:
            from whatskeep.organizer import Organizer

            org = Organizer()
            result = org.run()
            org.close()
            logger.info(
                f"Organized {result.organized} files, "
                f"{result.duplicates} duplicates, "
                f"{result.errors} errors"
            )
        except Exception as exc:
            logger.error(f"Organization failed: {exc}")

    threading.Thread(target=_work, daemon=True).start()


def _run_export():
    """Run full export in a background thread."""

    def _work():
        try:
            from whatskeep.organizer import Organizer

            org = Organizer()
            result = org.export_all()
            org.close()
            logger.info(f"Exported {result.organized} files")
        except Exception as exc:
            logger.error(f"Export failed: {exc}")

    threading.Thread(target=_work, daemon=True).start()


def _start_watcher():
    """Start the real-time watcher in a background thread."""

    def _work():
        try:
            from whatskeep.watcher import watch

            watch()
        except Exception as exc:
            logger.error(f"Watcher failed: {exc}")

    t = threading.Thread(target=_work, daemon=True)
    t.start()
    logger.info("Real-time watcher started")


def _show_stats():
    """Show stats via system notification or log."""
    try:
        from whatskeep.config import load_config, resolve_backup_dir
        from whatskeep.utils.fs import get_file_size_human
        from whatskeep.utils.stats import calculate_stats

        config = load_config()
        backup_dir = resolve_backup_dir(config)
        stats = calculate_stats(backup_dir)
        msg = (
            f"Files: {stats.total_files:,}\n"
            f"Size: {get_file_size_human(stats.total_bytes)}"
        )
        logger.info(f"Stats: {msg}")
        _notify("WhatsKeep Stats", msg)
    except Exception as exc:
        logger.error(f"Stats failed: {exc}")


def _check_update():
    """Check for updates."""
    try:
        from whatskeep.updater import check_for_update

        info = check_for_update()
        if info.is_newer:
            _notify("WhatsKeep Update", f"New version available: {info.latest_version}")
        else:
            _notify("WhatsKeep", "You are on the latest version.")
    except Exception as exc:
        logger.error(f"Update check failed: {exc}")


def _notify(title: str, message: str) -> None:
    """Show a desktop notification."""
    # Sanitize for shell/XML injection
    title = title.replace('"', "'").replace("<", "").replace(">", "").replace("&", "and")
    message = message.replace('"', "'").replace("<", "").replace(">", "").replace("&", "and")
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{message}" with title "{title}"',
                ],
                capture_output=True,
            )
        elif system == "Windows":
            # Use Windows toast notification via PowerShell
            toast_xml = (
                "<toast><visual><binding template='ToastText02'>"
                f"<text id='1'>{title}</text>"
                f"<text id='2'>{message}</text>"
                "</binding></visual></toast>"
            )
            ps = (
                "[Windows.UI.Notifications.ToastNotificationManager,"
                " Windows.UI.Notifications, ContentType=WindowsRuntime]"
                " | Out-Null; "
                f"$xml = New-Object Windows.Data.Xml.Dom.XmlDocument;"
                f" $xml.LoadXml('{toast_xml}');"
                " $n = [Windows.UI.Notifications.ToastNotification]"
                "::new($xml);"
                " [Windows.UI.Notifications.ToastNotificationManager]"
                "::CreateToastNotifier('WhatsKeep').Show($n)"
            )
            subprocess.run(["powershell", "-Command", ps], capture_output=True)
        else:
            subprocess.run(
                ["notify-send", title, message], capture_output=True
            )
    except Exception as exc:
        logger.debug(f"Notification failed: {exc}")


def run_tray() -> None:
    """Launch the system tray application."""
    import pystray

    icon_image = _get_icon_image()
    watcher_event = threading.Event()

    def on_run_now(icon, item):
        _notify("WhatsKeep", "Organizing files...")
        _run_organize()

    def on_export(icon, item):
        _notify("WhatsKeep", "Exporting all media...")
        _run_export()

    def on_start_watcher(icon, item):
        if not watcher_event.is_set():
            _start_watcher()
            watcher_event.set()
            _notify("WhatsKeep", "Real-time watcher started")
        else:
            _notify("WhatsKeep", "Watcher is already running")

    def on_open_folder(icon, item):
        _open_folder()

    def on_stats(icon, item):
        _show_stats()

    def on_update(icon, item):
        _check_update()

    def on_quit(icon, item):
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Run Now", on_run_now),
        pystray.MenuItem("Export All Media", on_export),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Start Real-time Watcher", on_start_watcher),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open WhatsKeep Folder", on_open_folder),
        pystray.MenuItem("Show Stats", on_stats),
        pystray.MenuItem("Check for Updates", on_update),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit),
    )

    icon = pystray.Icon("WhatsKeep", icon_image, "WhatsKeep", menu)

    # Auto-start watcher
    def _auto_start():
        import time

        time.sleep(2)
        _start_watcher()
        watcher_event.set()

    threading.Thread(target=_auto_start, daemon=True).start()

    logger.info("WhatsKeep tray app started")
    icon.run()
