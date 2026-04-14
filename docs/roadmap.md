# Roadmap

This document outlines the planned development milestones for WhatsKeep. Priorities may shift based on community feedback and contributions.

---

## v1.0.0 (Current)

The initial stable release. Core functionality is complete and tested.

- [x] Cross-platform file detection (macOS, Windows, Linux)
- [x] Modern and legacy WhatsApp filename pattern recognition
- [x] Chat export detection and organization
- [x] macOS ChatStorage.sqlite database reader (read-only, WAL-safe)
- [x] Windows and Linux database reader stubs
- [x] Contact/group folder organization with phone numbers
- [x] Unidentified file handling with date-based subfolders
- [x] SHA-256/MD5/BLAKE2b deduplication
- [x] Background daemon via launchd (macOS), Task Scheduler (Windows), systemd (Linux)
- [x] Interactive setup wizard (`whatskeep init`)
- [x] Dry-run mode (`whatskeep run --dry-run`)
- [x] Rich CLI with tables and colored output
- [x] Allowlist/blocklist backup modes
- [x] Media type filtering
- [x] Configuration via TOML (`~/.whatskeep/config.toml`)
- [x] Auto-update via GitHub Releases API
- [x] Diagnostics command (`whatskeep doctor`)
- [x] Storage statistics (`whatskeep stats`)
- [x] Contact listing (`whatskeep contacts`)
- [x] Log viewer (`whatskeep logs`)

---

## v1.1.0

Focus: **Windows database support and improved reliability**.

- [ ] Full Windows ChatStorage.sqlite reader implementation
- [ ] Linux database reader for common installation paths (snap, flatpak)
- [ ] Retry logic for cross-platform database access (locked/busy handling)
- [ ] File watcher integration with daemon mode (`whatskeep run --watch`)
- [ ] Configurable timestamp matching tolerance
- [ ] Notification system (native desktop notifications)
- [ ] Progress bar for large batch operations
- [ ] `whatskeep export` command to generate a CSV/JSON report of organized media

---

## v1.2.0

Focus: **Smart organization and user experience**.

- [ ] Fuzzy timestamp matching for improved contact identification rates
- [ ] Reverse-lookup: match files by content hash against database media hashes
- [ ] Customizable folder templates with more placeholders (`{date}`, `{year}`, `{month}`)
- [ ] Thumbnail generation for image and video files
- [ ] `whatskeep search` command to find files by contact, date, or type
- [ ] Interactive TUI mode using Textual or similar framework
- [ ] Shell completions (bash, zsh, fish, PowerShell)
- [ ] Localization support (Portuguese, Spanish)

---

## v1.3.0

Focus: **Advanced backup features**.

- [ ] Incremental backup with change tracking (avoid re-scanning unchanged files)
- [ ] Scheduled full scans (weekly/monthly digest)
- [ ] Backup to external drives with automatic detection
- [ ] Compression option for archived media (zip/tar.gz per contact)
- [ ] Retention policies (auto-delete old backups after N days)
- [ ] Conflict resolution UI for ambiguous file matches
- [ ] Plugin system for custom organization rules

---

## v2.0.0

Focus: **Multi-device and ecosystem expansion**.

- [ ] WhatsApp Business app support
- [ ] Telegram media organization (via Telegram Desktop database)
- [ ] Signal media organization
- [ ] Web-based dashboard for browsing organized media
- [ ] iCloud/Google Drive/OneDrive sync integration
- [ ] Mobile companion app (view organized media on phone)
- [ ] Multi-account support (multiple WhatsApp profiles)
- [ ] End-to-end encrypted backup archives
- [ ] REST API for integration with other tools

---

## Contributing to the Roadmap

Feature requests and suggestions are welcome. If you would like to work on any of the items above:

1. Check the [issues page](https://github.com/alissonlinneker/whatskeep/issues) for existing discussions
2. Open a new issue describing the feature and your proposed approach
3. Reference the roadmap version in your pull request

Priorities are influenced by community demand. If a feature matters to you, upvote or comment on its issue.
