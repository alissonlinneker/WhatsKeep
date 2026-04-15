"""GUI entry point — launches the system tray app directly.

Used by PyInstaller with --windowed to create a console-free executable.
Double-click on Windows/macOS opens the tray app without any terminal.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Configure loguru to file only (no stderr since there's no console)
from loguru import logger

logger.remove()
log_path = Path.home() / ".whatskeep" / "whatskeep-gui.log"
log_path.parent.mkdir(parents=True, exist_ok=True)
logger.add(
    str(log_path),
    level="INFO",
    rotation="10 MB",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}",
)


def main() -> None:
    """Launch the tray app."""
    try:
        from whatskeep.tray import run_tray

        run_tray()
    except Exception as exc:
        logger.error(f"GUI failed: {exc}")
        # On Windows, show error dialog since there's no console
        import platform

        if platform.system() == "Windows":
            import ctypes

            ctypes.windll.user32.MessageBoxW(  # type: ignore[union-attr]
                0,
                f"WhatsKeep failed to start:\n\n{exc}",
                "WhatsKeep Error",
                0x10,
            )
        sys.exit(1)


if __name__ == "__main__":
    main()
