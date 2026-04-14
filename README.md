<p align="center">
  <img src="docs/logo.svg" alt="WhatsKeep" width="400">
</p>

<p align="center">
  <strong>Never lose another photo, video, or audio from WhatsApp.</strong><br>
  Automatically organizes your WhatsApp media by contact and group — so you always know who sent what.
</p>

<p align="center">
  <a href="https://pypi.org/project/whatskeep/"><img src="https://img.shields.io/pypi/v/whatskeep" alt="PyPI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"></a>
  <a href="https://github.com/alissonlinneker/whatskeep"><img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey" alt="Platform"></a>
  <a href="reports/security-2026-04-14.md"><img src="https://img.shields.io/badge/shield_score-100%2F100-brightgreen" alt="Shield Score"></a>
</p>

---

## The Problem

WhatsApp loses media over time. Try to download an old photo and you get the dreaded "This media is no longer available" message -- even if you downloaded it before. Old photos, videos, and audio messages silently become unavailable. This is a chronic problem affecting millions of users.

When you log into WhatsApp on a secondary device (WhatsApp Web, linked devices), your conversations only stay for roughly 90 days and gradually disappear. Worse, WhatsApp does not sync conversations from before the date you linked the device -- that history simply never shows up.

Downloaded media from WhatsApp Desktop goes straight to the Downloads folder with generic names like:

```
WhatsApp Image 2026-04-08 at 14.20.43.jpeg
WhatsApp Audio 2026-04-10 at 09.15.22.opus
```

No contact information attached, no organization. It is impossible to know who sent what.

When someone uses "delete for everyone," the media vanishes in seconds from your device too. If you didn't capture it beforehand, it's gone.

WhatsApp's "disappearing messages" feature makes this even worse. Entire conversations -- including every photo, video, and voice note shared within them -- are automatically wiped after 24 hours, 7 days, or 90 days depending on the chat setting. Because WhatsKeep captures media in real time as it arrives, all content is preserved before the auto-deletion timer expires.

If you need these media files as evidence in court, simple screenshots are increasingly being rejected (Brazilian Superior Court of Justice rulings, 2024-2025). The secure alternative -- a notarial act (ata notarial) -- costs between BRL 500 and BRL 2,000+, and it only works if the content still exists at the time of certification.

WhatsKeep solves this by perpetuating **all** media in an organized way (by contact and group), capturing in real time before deletion, and maintaining a chain of custody for potential legal use.

---

## The Solution

WhatsKeep monitors your Downloads folder, reads the local WhatsApp Desktop database (read-only), and automatically organizes each file into a clear structure:

```
~/WhatsKeep/
├── Contacts/
│   ├── John Smith (+1 555 123-4567)/
│   │   ├── Audio/
│   │   ├── Image/
│   │   ├── Video/
│   │   └── _evidence/
│   └── Sarah Connor (+1 555 987-6543)/
│       ├── Image/
│       └── Video/
├── Groups/
│   ├── Weekend Crew/
│   │   ├── Audio/
│   │   │   ├── [David (+1 555 222-3333)] WhatsApp Audio 2026-04-08 at 14.20.43.opus
│   │   │   └── [Emma] WhatsApp Audio 2026-04-08 at 15.30.00.opus
│   │   └── Image/
│   └── Family Group/
│       ├── Image/
│       └── Video/
├── _Unidentified/
│   └── Image/
│       └── 2026-04/
│           └── WhatsApp Image 2026-04-05 at 08.00.00.jpeg
├── _Chat Exports/
│   └── Family Group/
│       └── WhatsApp Chat - Family Group.zip
└── _Evidence/
    └── full_export_2026-04-14_120000/
        ├── manifest.json
        ├── SHA256SUMS.txt
        └── chain_of_custody.json
```

Each file is attributed to the person or group that sent it. In group chats, the sender's name is prefixed to the filename. Unidentified files go to `_Unidentified/`, organized by date.

---

## Features

### 1. Automatic organization by contact and group

Detects WhatsApp files by filename patterns (modern Desktop format, legacy Android format, variations with hyphens, underscores, and spaces) and correlates them with the WhatsApp Desktop database to identify the corresponding contact or group. Files are moved to the correct folder automatically.

### 2. Sender identification in groups

For group files, WhatsKeep prefixes the filename with the sender's name and phone number. For example:

```
[David (+1 555 222-3333)] WhatsApp Audio 2026-04-10 at 09.15.22.opus
[Emma] WhatsApp Image 2026-04-08 at 14.20.43.jpeg
```

This way you know exactly who sent each piece of media within a group.

### 3. Name resolution

When a contact is not saved in your address book, WhatsKeep uses the WhatsApp **push name** (the name the user has set in their own profile) as a fallback. This prevents folders from being labeled with raw phone numbers when the contact is known to WhatsApp but not to your address book.

### 4. Real-time monitoring

The watchdog-based daemon captures files in under 1 second after they appear in your Downloads folder. The strategy is:

1. File appears in Downloads
2. Immediate copy to `_staging/` (preserves the file BEFORE "delete for everyone" can remove it)
3. Queries the database to identify the contact
4. Moves the file to the organized destination
5. Removes the original from Downloads
6. Logs the operation in the tracking database

This approach ensures that even media deleted seconds after being sent is preserved.

### 5. Full history export

The `whatskeep export` command copies ALL media from the WhatsApp Desktop internal storage (`Message/Media/` directory), organizing by contact and group. Ideal for backing up your entire history at once. Originals are never moved or deleted -- only copied. Safe to run multiple times (skips already-exported files).

### 6. Deletion detection

WhatsKeep tracks all organized files and periodically checks whether the original message still exists in the WhatsApp database. When it detects that a message has been deleted from the chat:

- Renames the file with a `[DELETED]` prefix
- On macOS, adds a red Finder tag for immediate visibility
- Logs the detection timestamp in the tracking database

Includes a safety mechanism: if more than 50% of tracked files appear "deleted," WhatsKeep assumes there is a database access issue (not actual deletions) and aborts the check.

### 7. Digital chain of custody

A complete evidence preservation system inspired by Article 158-A of the Brazilian Code of Criminal Procedure (CPP) and ISO 27037:

- **SHA-256 hash** of each file at the moment of organization
- **Chronological custody event log** (who, when, how, hostname, platform)
- **Sidecar `.custody.json`** per file with full metadata (hash, size, date, system)
- **Integrity verification** -- recalculates hashes and compares against original records to detect tampering
- All events are stored in a local SQLite database with WAL mode

### 8. Evidence export

Generates structured packages ready for lawyers or court presentation:

- `manifest.json` -- full inventory with hash, integrity status, contact data, and deletion detection
- `SHA256SUMS.txt` -- file compatible with `sha256sum -c` for batch verification
- `chain_of_custody.json` -- complete chronological log of all custody events

The export can be scoped to a specific contact (`--contact`) or complete (`--all`). Each package includes a disclaimer explaining that it does not replace a notarized certificate or certified platforms.

### 9. SHA-256 deduplication

Two-step hash verification before removing duplicates:

- Compares the SHA-256 hash of the source file against the destination
- Verifies file stability (size is unchanged) before deleting
- Audit log of each duplicate removed
- Supports SHA-256 and BLAKE2b algorithms

### 10. Cross-platform daemon

- **macOS**: launchd (with auto-restart)
- **Windows**: Task Scheduler
- **Linux**: systemd

Install, start, stop, and remove via simple commands (`whatskeep start`, `whatskeep stop`, `whatskeep uninstall`).

### 11. Media type filtering

Granular configuration of which types to process:

| Type | Default |
|------|---------|
| `image` | Enabled |
| `audio` | Enabled |
| `video` | Enabled |
| `document` | Enabled |
| `sticker` | Disabled |
| `gif` | Disabled |
| `voice_note` | Enabled |

### 12. Selective backup

Three backup modes:

- **`all`** -- organizes media from all contacts (default)
- **`allowlist`** -- organizes only listed contacts
- **`blocklist`** -- organizes all contacts except those listed

### 13. Dry-run

Run `whatskeep run --dry-run` or `whatskeep export --dry-run` to preview exactly what would be done without moving or copying any files.

### 14. Doctor

Comprehensive environment diagnostics:

- Python version (>= 3.10)
- Supported platform
- WhatsApp database access
- Downloads and Backup folder existence
- Daemon status
- Configuration validity
- Disk space (> 1 GB free)

### 15. Auto-update

Checks for updates via the GitHub Releases API. Can be configured to check automatically every N hours or manually via `whatskeep update`.

### 16. 100% local and private

- Reads the WhatsApp database in **read-only mode** (never writes)
- Accesses only media metadata: filename, timestamp, contact name, phone number
- **Never sends data to any server**
- **No analytics, no telemetry, no tracking**
- **No accounts, no sign-up, no cloud storage**
- The only network request is the optional update check against GitHub (can be disabled)
- Open source (MIT)

---

## Installation

### macOS

Python 3.10+ is usually pre-installed. Open Terminal and run:

```bash
pip install whatskeep
```

If `pip` is not found, install Python first via [Homebrew](https://brew.sh/):

```bash
brew install python
pip install whatskeep
```

### Windows

1. **Install Python** (if you don't have it):
   - Download from [python.org/downloads](https://www.python.org/downloads/) (click the big yellow button)
   - **Important**: Check the box **"Add Python to PATH"** during installation
   - Click "Install Now"

2. **Install WhatsKeep**: Open Command Prompt (search "cmd" in Start Menu) or PowerShell and run:

```bash
pip install whatskeep
```

3. **Verify**: Type `whatskeep version` and press Enter. You should see the version number.

> **Tip**: If `pip` is not recognized, try `python -m pip install whatskeep` instead.

### Linux

```bash
pip install whatskeep
```

On some distributions you may need `pip3` instead of `pip`, or install Python first:

```bash
# Ubuntu/Debian
sudo apt install python3-pip
pip3 install whatskeep

# Fedora
sudo dnf install python3-pip
pip3 install whatskeep
```

### From source (for developers)

```bash
git clone https://github.com/alissonlinneker/whatskeep.git
cd whatskeep
pip install -e .        # or: uv pip install -e .
```

### Standalone binary (planned)

Distribution as a single executable (no Python required) is planned for a future release.

---

## WhatsApp Desktop Setup

WhatsKeep requires WhatsApp Desktop to be installed and configured to download media automatically. Without this, media files will not appear in your Downloads folder.

### macOS

1. Install [WhatsApp Desktop](https://apps.apple.com/app/whatsapp-messenger/id310633997) from the App Store or download from [whatsapp.com/download](https://www.whatsapp.com/download)
2. Open WhatsApp Desktop and sign in
3. Go to **Settings** (gear icon) > **Storage and Data**
4. Under **Automatic media download**, enable all types:
   - Photos: **Always**
   - Audio: **Always**
   - Videos: **Always**
   - Documents: **Always**
5. Verify: send a test image to yourself and confirm it appears in `~/Downloads`

### Windows

1. Install [WhatsApp Desktop](https://apps.microsoft.com/detail/whatsapp/9NKSQGP7F2NH) from the Microsoft Store or download from [whatsapp.com/download](https://www.whatsapp.com/download)
2. Open WhatsApp Desktop and sign in
3. Go to **Settings** > **Storage and Data**
4. Enable automatic download for all media types
5. Verify: downloaded media should appear in `%USERPROFILE%\Downloads`

### Linux

1. Install WhatsApp Desktop via snap (`snap install whatsapp-for-linux`) or the official binary
2. Open WhatsApp Desktop and sign in
3. Enable automatic download under **Settings** > **Storage and Data**
4. Note: database support on Linux is best-effort; contact identification may be limited

---

## Getting Started

```bash
# Interactive setup wizard
whatskeep init

# Diagnose the environment
whatskeep doctor

# Organize existing files in the Downloads folder
whatskeep run

# Export the ENTIRE WhatsApp media history
whatskeep export

# Install and start the real-time monitoring daemon
whatskeep start
```

Done. WhatsKeep now automatically organizes every new WhatsApp media file as soon as it arrives.

---

## Command Reference

### Organization

| Command | Description |
|---------|-------------|
| `whatskeep init` | Interactive first-time setup wizard |
| `whatskeep run` | Run organization once (scans Downloads and moves files) |
| `whatskeep run --dry-run` | Preview changes without moving any files |
| `whatskeep run --watch` | Monitor the Downloads folder continuously in real time |
| `whatskeep run --verbose` | Run with DEBUG-level logging |
| `whatskeep export` | Export the ENTIRE media history from WhatsApp internal storage |
| `whatskeep export --dry-run` | Preview the export without copying any files |

### Daemon

| Command | Description |
|---------|-------------|
| `whatskeep start` | Install and start the background daemon |
| `whatskeep stop` | Stop the daemon |
| `whatskeep status` | Show daemon status and last execution |

### Information

| Command | Description |
|---------|-------------|
| `whatskeep stats` | Show storage statistics for the backup directory |
| `whatskeep contacts` | List contacts and groups detected in the WhatsApp database |
| `whatskeep contacts --filter "John"` | Filter contacts by name |

### Configuration

| Command | Description |
|---------|-------------|
| `whatskeep config show` | Display current configuration in TOML format |
| `whatskeep config edit` | Open the config file in the default editor |
| `whatskeep config reset` | Reset configuration to defaults |

### Evidence

| Command | Description |
|---------|-------------|
| `whatskeep evidence status` | Show custody tracking statistics |
| `whatskeep evidence hash` | Generate SHA-256 hashes for pending files |
| `whatskeep evidence verify` | Verify integrity of all tracked files |
| `whatskeep evidence export --contact "John Smith"` | Export evidence package for a specific contact |
| `whatskeep evidence export --all` | Export complete evidence package |

### Maintenance

| Command | Description |
|---------|-------------|
| `whatskeep update` | Check for and install updates |
| `whatskeep update --check` | Only check whether updates are available |
| `whatskeep update --force` | Force re-check ignoring cache interval |
| `whatskeep logs` | Show recent log entries |
| `whatskeep logs --tail` | Follow the log in real time |
| `whatskeep doctor` | Diagnose common configuration issues |
| `whatskeep version` | Show version and platform information |
| `whatskeep uninstall` | Remove the daemon and optionally delete configuration |

---

## Configuration

WhatsKeep stores its configuration in `~/.whatskeep/config.toml`. Run `whatskeep init` to create the file interactively, or edit it directly.

```toml
[general]
# Interface language
language = "en"
# Downloads folder ("auto" detects ~/Downloads automatically)
download_dir = "auto"
# Folder where organized files will be stored
backup_dir = "~/WhatsKeep"

[monitoring]
# Interval in seconds between scans in daemon mode
interval = 10
# Process files already in the Downloads folder on first run
process_existing = true

[backup]
# Backup mode: "all" (everyone), "allowlist" (only listed), "blocklist" (except listed)
mode = "all"
# Contacts to include (when mode = "allowlist")
allowlist = []
# Contacts to exclude (when mode = "blocklist")
blocklist = []

[media_types]
# Media types to organize (true = enabled, false = disabled)
image = true
audio = true
video = true
document = true
sticker = false
gif = false
voice_note = true

[organization]
# Folder structure template
folder_template = "{contact}/{type}"
# Include phone number in the contact folder name
show_phone = true
# Suffix for group folders (currently unused — groups use the Groups/ prefix instead)
group_suffix = "(group)"
# Folder name for unidentified files
unidentified_folder = "_Unidentified"
# Organize unidentified files into YYYY-MM subfolders
unidentified_by_date = true

[deduplication]
# Enable duplicate detection and removal
enabled = true
# Hash algorithm for deduplication ("sha256" or "blake2b")
algorithm = "sha256"

[auto_update]
# Check for updates automatically
enabled = true
# Update channel ("stable" or "beta")
channel = "stable"
# Interval in hours between automatic checks
check_interval_hours = 24

[notifications]
# Enable desktop notifications
enabled = true
# Notify when organizing files
on_organize = false
# Notify on errors
on_error = true
# Notify when an update is available
on_update = true

[logging]
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
level = "INFO"
# Maximum log file size in MB (automatic rotation)
max_size_mb = 10
# Log retention in days
retention_days = 30
```

---

## Digital Evidence Preservation

### Layered Strategy

Digital evidence preservation works best through progressive layers of increasing cost and legal strength:

| Layer | Method | Cost | Value |
|-------|--------|------|-------|
| **1 - WhatsKeep** | Organized backup + SHA-256 hash + metadata + chain of custody log | Free (open-source) | Protection against loss, organization, technical foundation |
| **2 - OpenTimestamps** | Hash anchored in blockchain (Bitcoin) | Free | Immutable temporal proof that the content existed at that point in time |
| **3 - Verifact / e-Not Provas** | Certified platform with isolated environment or public trust authority (services recognized under Brazilian law) | BRL 4-97/session | Independent chain of custody, accepted in Brazilian courts |
| **4 - Notarized certificate (Ata notarial)** | Sworn document prepared by a notary public (a legally recognized official under Brazilian civil law) | BRL 500-2,000+ | Public trust authority + in-person analysis by the notary |

WhatsKeep operates as **Layer 1**: the automatic, free foundation that preserves your files before they are lost, generates hashes for integrity verification, and documents the chain of custody. Higher layers can be added as the legal needs of the case require.

### What WhatsKeep CAN do

- Automatically generate SHA-256 hashes for each file at the moment of copy
- Record full metadata (timestamp, device, OS, user, original path)
- Create a chronological, auditable chain of custody log
- Periodically verify that hashes have not changed (tampering detection)
- Export structured evidence packages for lawyers
- Detect when messages are deleted from the chat and mark the corresponding files

### What WhatsKeep CANNOT do

- **Does not replace a notarized certificate**: the software does not carry public trust authority
- **Does not guarantee authenticity of the original content**: the hash proves the file has not changed AFTER the copy, but does not prove that the WhatsApp content was authentic before the copy
- **Is not an isolated environment**: since it runs on the user's machine, an expert could argue the environment may have been compromised
- **Does not replace forensic analysis**: in cases of serious contestation, a court-appointed forensic expert will be needed
- **Does not guarantee full ISO 27037 compliance**: independent third-party auditability is missing

### Legal Precedent (Brazilian Courts)

Brazil's Superior Court of Justice (STJ) has progressively demanded rigorous chain of custody for digital evidence. While these rulings are specific to Brazilian law, they reflect a global trend toward stricter standards for digital evidence in court:

- **HC 828.054/RN (May 2024)** -- Cell phone screenshots extracted without proper methodology: deemed inadmissible
- **HC 1.036.370 (September 2025)** -- Conviction based solely on WhatsApp screenshots: fully overturned
- **6th Panel (December 2024)** -- Absence of chain of custody renders digital evidence null
- **5th Panel (2025)** -- Private-party screenshots are valid if confirmed in court and with no evidence of tampering
- **STJ (September 2024)** -- Digital signatures with SHA-256 outside ICP-Brasil (the Brazilian Public Key Infrastructure) are valid

For the full research, see [docs/research-digital-evidence-brazil.md](docs/research-digital-evidence-brazil.md).

### Disclaimer

> WhatsKeep is a media backup and organization tool. The hashes and metadata it generates assist with integrity preservation but do not replace a notarized certificate, forensic analysis, or certified platforms (such as Verifact or e-Not Provas) for use as judicial evidence. Consult a lawyer for guidance on evidence preservation for your specific case.

---

## How It Works

### 1. File detection by filename patterns

WhatsKeep scans the Downloads folder looking for files that match known WhatsApp naming patterns:

- **Modern format (Desktop)**: `WhatsApp Image 2026-04-08 at 14.20.43.jpeg`
- **Modern format with hyphens**: `WhatsApp-Image-2024-01-15-at-21.34.04.jpg`
- **Modern format with underscores**: `WhatsApp_Image_2024-06-24_at_18.54.07.png`
- **Legacy format (Android)**: `IMG-20260408-WA0032.jpg`
- **Chat exports**: `WhatsApp Chat - Contact Name.zip`

Duplicate indices like `(1)` are also handled.

### 2. Database correlation

WhatsKeep reads the local WhatsApp Desktop database (SQLite, read-only, with WAL for safe concurrent access) and builds a timestamp-to-contact lookup table. The timestamp extracted from the filename is converted from Unix format to Core Data epoch (used internally by WhatsApp on macOS), which starts on January 1, 2001 (978307200 seconds offset from the Unix epoch).

| Platform | Database location |
|----------|-------------------|
| macOS | `~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite` |
| Windows | `%AppData%\WhatsApp\databases\` or `%LocalAppData%\Packages\5319275A.WhatsAppDesktop_*\LocalCache\` (auto-detected) |
| Linux | Best-effort; path varies depending on installation method |

### 3. Timestamp tolerance

The correlation uses a +/- 3-second tolerance between the filename timestamp and the database record. This compensates for small differences between the moment the message was received and the moment the file was saved.

### 4. Push name fallback

When a contact is not saved in the user's address book, the name displayed in the database is just the phone number. WhatsKeep queries the `ZWAPROFILEPUSHNAME` table to obtain the name the user has set in their own WhatsApp profile, using it as the display name.

### 5. Sticker detection via ZMESSAGETYPE

Stickers do not have a distinct filename prefix. WhatsKeep identifies stickers by the `ZMESSAGETYPE = 15` field in the database, allowing it to filter or organize them correctly.

### 6. Database access privacy

WhatsKeep opens the database with `mode=ro` (read-only) in the SQLite connection URI. It does not access text message content -- only media metadata (contact name, timestamp, file path, message type). No query touches the message content tables.

---

## Privacy

WhatsKeep is 100% local. Here is exactly what it does and does not do:

- Reads the WhatsApp database in **read-only mode** (never writes)
- Accesses only media metadata: filename, timestamp, contact name, phone number
- Moves and copies files between local directories on your machine
- **Never sends data to any server**
- **No analytics, no telemetry, no tracking**
- **No accounts, no sign-up, no cloud storage**
- The only network request is the optional update check against the GitHub Releases API (can be disabled in `config.toml`)
- Open source under the MIT license -- you can audit every line

Your media stays on your machine. Always.

---

## Roadmap

### v1.0.0 (Current)

- Cross-platform file detection (macOS, Windows, Linux)
- Modern and legacy WhatsApp filename pattern recognition
- Chat export detection and organization
- macOS ChatStorage.sqlite database reader (read-only, WAL-safe)
- Windows and Linux database readers (auto-detect schema, best-effort)
- Organization by contact/group with phone numbers
- Unidentified file handling with date-based subfolders
- SHA-256/BLAKE2b deduplication
- Background daemon via launchd (macOS), Task Scheduler (Windows), systemd (Linux)
- Interactive setup wizard (`whatskeep init`)
- Dry-run mode (`whatskeep run --dry-run`)
- CLI with colored output and tables via Rich
- Allowlist/blocklist backup modes
- Media type filtering
- TOML configuration (`~/.whatskeep/config.toml`)
- Auto-update via GitHub Releases API
- Diagnostics command (`whatskeep doctor`)
- Storage statistics (`whatskeep stats`)
- Contact listing (`whatskeep contacts`)
- Log viewer (`whatskeep logs`)
- Real-time monitoring with watchdog (`whatskeep run --watch`)
- Full media history export (`whatskeep export`)
- Message deletion detection with visual tagging
- Digital chain of custody with SHA-256 hashing and event logging
- Evidence package export for legal use
- Name resolution via WhatsApp push name

### v1.1.0 (Planned)

Focus: **Evidence strength and reliability improvements**.

- OpenTimestamps integration (blockchain timestamp anchoring — evidence Layer 2)
- Configurable timestamp matching tolerance
- Native desktop notification system
- Progress bar for large batch operations
- Re-correlate unidentified files on subsequent runs
- Expanded test coverage (target >80%)
- Homebrew formula, winget manifest, snap package

### v1.2.0 (Planned)

Focus: **Smart organization and user experience**.

- Fuzzy timestamp matching for higher identification rates
- Reverse-lookup: match by content hash against database hashes
- Customizable folder templates with more placeholders (`{date}`, `{year}`, `{month}`)
- Thumbnail generation for images and videos
- `whatskeep search` command to find files by contact, date, or type
- Interactive TUI mode
- Shell completions (bash, zsh, fish, PowerShell)
- Localization support (Portuguese, Spanish)

### v1.3.0 (Planned)

Focus: **Advanced backup features**.

- Incremental backup with change tracking
- Scheduled scans (weekly/monthly digest)
- External drive backup with automatic detection
- Archived media compression (zip/tar.gz per contact)
- Retention policies (auto-delete after N days)
- Conflict resolution UI for ambiguous matches
- Plugin system for custom organization rules

### v2.0.0 (Planned)

Focus: **Multi-device and ecosystem expansion**.

- WhatsApp Business support
- Telegram media organization
- Signal media organization
- Web dashboard for browsing organized media
- iCloud/Google Drive/OneDrive integration
- Mobile companion app
- Multiple WhatsApp account support
- End-to-end encrypted backup
- REST API for integration with other tools

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for information about:

- Development environment setup
- Running tests (`pytest`)
- Code style (Ruff, mypy)
- Submitting pull requests

### Development setup

```bash
git clone https://github.com/alissonlinneker/whatskeep.git
cd whatskeep
pip install -e ".[dev]"

# Run tests
pytest

# Lint and type-check
ruff check .
mypy src/whatskeep
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

Copyright (c) 2026 Alisson Linneker.
