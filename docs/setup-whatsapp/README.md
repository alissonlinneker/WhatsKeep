# Setting Up WhatsApp Desktop for WhatsKeep

WhatsKeep requires WhatsApp Desktop to be installed and configured to automatically download media files. Without this setup, media files will not appear in your Downloads folder, and WhatsKeep will have nothing to organize.

## Why This Step Matters

By default, WhatsApp Desktop does not save media to your local filesystem. You need to explicitly enable auto-download so that every photo, video, audio message, and document is saved to your Downloads folder as it arrives. This is the mechanism WhatsKeep relies on to detect and organize your media.

Additionally, WhatsKeep reads the local WhatsApp database (in read-only mode) to correlate files with contacts. This database is only created when WhatsApp Desktop is installed and signed in.

## Platform Guides

Choose your platform for step-by-step instructions:

- **[macOS](macos.md)** -- App Store or direct download, launchd daemon
- **[Windows](windows.md)** -- Microsoft Store or direct download, Task Scheduler daemon
- **[Linux](linux.md)** -- Snap, Flatpak, or direct binary, systemd daemon

## Quick Checklist

Regardless of platform, verify these items before running WhatsKeep:

1. WhatsApp Desktop is installed (not just the web version in a browser)
2. You are signed in and your chats have synced
3. Auto-download is enabled for all media types (Photos, Audio, Videos, Documents)
4. A test image sent to yourself appears in your Downloads folder
5. `whatskeep doctor` shows "WhatsApp DB accessible: OK"

If any of these fail, refer to the platform-specific guide for detailed troubleshooting.
