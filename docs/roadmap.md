# Roadmap

Planned development milestones for WhatsKeep. Priorities may shift based on community feedback.

---

## v1.0.0 (Current)

The initial stable release with full cross-platform support.

### Core
- [x] Cross-platform file detection (macOS, Windows, Linux)
- [x] Modern and legacy WhatsApp filename pattern recognition
- [x] Chat export detection and organization
- [x] Contacts/ and Groups/ folder structure (no duplicated phone numbers)

### Database Readers (all platforms)
- [x] macOS ChatStorage.sqlite reader (read-only, WAL-safe, retry with backoff)
- [x] Windows database reader (standalone + UWP paths, auto-detect schema)
- [x] Linux database reader (snap, flatpak, .config paths, auto-detect schema)
- [x] Push name fallback for contacts not saved in address book
- [x] Sender identification in group messages via ZWAPROFILEPUSHNAME
- [x] Sticker detection via ZMESSAGETYPE=15

### Real-time & Export
- [x] Real-time watchdog daemon captures files in <1 second
- [x] Full history export from WhatsApp internal storage (`whatskeep export`)
- [x] Background daemon: launchd (macOS), Task Scheduler (Windows), systemd (Linux)
- [x] Watch mode (`whatskeep run --watch`) for continuous monitoring

### Evidence & Security
- [x] SHA-256 chain of custody with per-file .custody.json sidecars
- [x] Deletion detection: tags files with [DELETED] + Finder red tag on macOS
- [x] Evidence export packages per contact (manifest + SHA256SUMS + custody log)
- [x] Integrity verification (`whatskeep evidence verify`)
- [x] Deduplication with double-hash verification and stability checks
- [x] Path traversal prevention (validate_dest_within_root)
- [x] SQLite busy_timeout + threading locks for concurrent access
- [x] 50% safety threshold for false-positive deletion detection

### CLI
- [x] Interactive setup wizard (`whatskeep init`)
- [x] Dry-run mode for all operations
- [x] Rich tables and colored output
- [x] 19 commands: init, run, export, start, stop, status, stats, contacts, config (show/edit/reset), evidence (status/hash/verify/export), update, logs, doctor, version, uninstall
- [x] Configurable media type filtering (sticker and gif disabled by default)
- [x] Allowlist/blocklist backup modes
- [x] Auto-update via GitHub Releases API (configurable, --check and --force flags)

### Documentation & CI
- [x] Comprehensive README with all features documented
- [x] WhatsApp Desktop setup guides (macOS, Windows, Linux)
- [x] Configuration reference, troubleshooting guide
- [x] Digital evidence research (Brazilian law, STJ jurisprudence)
- [x] GitHub Actions CI (matrix: 3 OS x 4 Python versions)
- [x] Release workflow (PyInstaller binaries + PyPI publish)
- [x] Security audit: Shield score 100/100

---

## v1.1.0

Focus: **Reliability, evidence strength, and test coverage**.

- [ ] OpenTimestamps integration (blockchain timestamp anchoring — evidence Layer 2)
- [ ] Resolve DB lookup in launchd daemon context (macOS permissions investigation)
- [ ] Re-correlate _Unidentified files with contacts on subsequent runs
- [ ] Configurable timestamp matching tolerance (currently fixed at +/-3 seconds)
- [ ] Native desktop notifications (macOS/Windows/Linux)
- [ ] Progress bar for large batch operations (export, hash, verify)
- [ ] Expanded test coverage (target >80%, ~65 new tests for tracker, evidence, watcher)
- [ ] Homebrew formula, winget manifest, snap package

---

## v1.2.0

Focus: **Smart organization and user experience**.

- [ ] Fuzzy timestamp matching for improved contact identification
- [ ] Reverse-lookup: match files by content hash against database media hashes
- [ ] Customizable folder templates (`{date}`, `{year}`, `{month}`)
- [ ] `whatskeep search` command to find files by contact, date, or type
- [ ] Interactive TUI mode (Textual)
- [ ] Shell completions (bash, zsh, fish, PowerShell)
- [ ] Localization support (Portuguese, Spanish)
- [ ] Thumbnail generation for image and video files

---

## v1.3.0

Focus: **Advanced backup features**.

- [ ] Incremental backup with change tracking
- [ ] Scheduled full scans (weekly/monthly digest)
- [ ] Backup to external drives with automatic detection
- [ ] Compression option for archived media (zip/tar.gz per contact)
- [ ] Retention policies (auto-delete old backups after N days)
- [ ] Plugin system for custom organization rules

---

## v2.0.0

Focus: **Multi-device and ecosystem expansion**.

- [ ] WhatsApp Business app support
- [ ] Telegram media organization
- [ ] Signal media organization
- [ ] Web-based dashboard for browsing organized media
- [ ] Cloud sync (iCloud, Google Drive, OneDrive)
- [ ] Mobile companion app
- [ ] Multi-account support
- [ ] End-to-end encrypted backup archives
- [ ] REST API for integration with other tools

---

## Contributing

Feature requests welcome. Check the [issues page](https://github.com/alissonlinneker/whatskeep/issues) for existing discussions or open a new issue.
