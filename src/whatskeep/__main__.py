"""Allow running as `python -m whatskeep`.

This is the CLI entry point. For the GUI (system tray), use gui.py.
"""

from whatskeep.cli import app

app()
