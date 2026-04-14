# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-14

### Added
- Cross-platform WhatsApp media detection (modern + legacy filename patterns)
- WhatsApp database correlation for macOS, Windows, and Linux
- Automatic organization by contact/group and media type
- Selective backup with allowlist/blocklist by contact
- Media type filtering (image, audio, video, document, sticker, voice note)
- Background daemon support (launchd on macOS, Task Scheduler on Windows, systemd on Linux)
- Interactive setup wizard (`whatskeep init`)
- TOML configuration at `~/.whatskeep/config.toml`
- Auto-update from GitHub Releases
- Comprehensive CLI with commands: init, run, start, stop, status, stats, config, contacts, update, logs, uninstall, version, doctor
- Dry-run mode for safe preview
- SHA-256 file deduplication
- File system watcher for real-time monitoring
- Diagnostic doctor command
- Storage statistics
- Comprehensive logging with rotation

[1.0.0]: https://github.com/alissonlinneker/whatskeep/releases/tag/v1.0.0
