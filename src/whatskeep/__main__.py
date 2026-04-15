"""Allow running as `python -m whatskeep`.

When launched as a standalone binary (double-click), opens the system tray app.
When launched from terminal with arguments, runs the CLI.
"""

import sys


def main() -> None:
    # If launched with no arguments (e.g. double-click on Windows/macOS),
    # start the tray app instead of showing CLI help
    if len(sys.argv) == 1 and not sys.stdin.isatty():
        # Running as GUI (no terminal attached)
        from whatskeep.tray import run_tray

        run_tray()
    else:
        from whatskeep.cli import app

        app()


main()
