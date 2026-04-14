# Configuration Reference

WhatsKeep is configured via a TOML file located at `~/.whatskeep/config.toml`. This file is created automatically when you run `whatskeep init`, or you can create it manually.

## Managing Configuration

```bash
# Create config interactively
whatskeep init

# View current config
whatskeep config show

# Open in your editor ($EDITOR, defaults to nano/notepad)
whatskeep config edit

# Reset to defaults
whatskeep config reset
```

## Full Configuration Reference

Below is every section and option, with defaults and explanations.

---

### `[general]`

Top-level settings for directories and language.

| Key            | Type   | Default        | Description                                                                                    |
| -------------- | ------ | -------------- | ---------------------------------------------------------------------------------------------- |
| `language`     | string | `"en"`         | Interface language. Currently only `"en"` is supported.                                        |
| `download_dir` | string | `"auto"`       | Path to the folder WhatsApp Desktop saves media to. `"auto"` resolves to `~/Downloads` on all platforms (respects `XDG_DOWNLOAD_DIR` on Linux). Set an absolute path to override. |
| `backup_dir`   | string | `"~/WhatsKeep"` | Where organized files are stored. Supports `~` expansion.                                     |

**Example:**

```toml
[general]
language = "en"
download_dir = "/Volumes/External/Downloads"
backup_dir = "~/WhatsKeep"
```

---

### `[monitoring]`

Controls the background monitoring behavior.

| Key                | Type    | Default | Description                                                                             |
| ------------------ | ------- | ------- | --------------------------------------------------------------------------------------- |
| `interval`         | integer | `10`    | Seconds between file system scans when running as a daemon. Lower values detect files faster but use more CPU. |
| `process_existing` | boolean | `true`  | When `true`, the first run processes files already present in the Downloads folder. When `false`, only newly created files are organized. |

**Example:**

```toml
[monitoring]
interval = 30
process_existing = false
```

---

### `[backup]`

Controls which contacts and groups are included in the backup.

| Key         | Type           | Default | Description                                                                                   |
| ----------- | -------------- | ------- | --------------------------------------------------------------------------------------------- |
| `mode`      | string         | `"all"` | Backup strategy. One of: `"all"` (every contact), `"allowlist"` (only listed contacts), or `"blocklist"` (everyone except listed contacts). |
| `allowlist` | array of strings | `[]`  | Contact and group names to include. Only used when `mode = "allowlist"`.                      |
| `blocklist` | array of strings | `[]`  | Contact and group names to exclude. Only used when `mode = "blocklist"`.                      |

**Important:** Names must match exactly as they appear in your WhatsApp contacts. Use `whatskeep contacts` to see the detected names.

**Examples:**

Back up only specific contacts:

```toml
[backup]
mode = "allowlist"
allowlist = ["John Smith", "Family Group", "Work Team"]
```

Back up everyone except specific contacts:

```toml
[backup]
mode = "blocklist"
blocklist = ["Spam Group", "Noisy Chat"]
```

---

### `[media_types]`

Toggle which media types WhatsKeep should organize. Set to `false` to skip a type entirely.

| Key          | Type    | Default | Description                                  |
| ------------ | ------- | ------- | -------------------------------------------- |
| `image`      | boolean | `true`  | JPEG, PNG, WebP, GIF, HEIC                  |
| `audio`      | boolean | `true`  | OPUS, OGG, M4A, MP3, AAC, WAV               |
| `video`      | boolean | `true`  | MP4, MOV, AVI, 3GP                           |
| `document`   | boolean | `true`  | PDF, DOCX, XLSX, PPTX, TXT, ZIP             |
| `sticker`    | boolean | `false` | WebP sticker files                            |
| `voice_note` | boolean | `true`  | Voice messages (OPUS/OGG from WhatsApp PTT)  |

**Example:**

```toml
[media_types]
image = true
audio = true
video = true
document = false
sticker = false
voice_note = false
```

---

### `[organization]`

Controls how files are organized into folders.

| Key                   | Type    | Default              | Description                                                                                       |
| --------------------- | ------- | -------------------- | ------------------------------------------------------------------------------------------------- |
| `folder_template`     | string  | `"{contact}/{type}"` | Template for the folder hierarchy under the backup directory. `{contact}` and `{type}` are placeholders. |
| `show_phone`          | boolean | `true`               | Append the phone number to contact folder names, e.g., `John Smith (+1 555 123-4567)`.            |
| `group_suffix`        | string  | `"(group)"`          | Text appended to group chat folder names, e.g., `Family Group (group)`.                           |
| `unidentified_folder` | string  | `"_Unidentified"`    | Folder name for files that could not be matched to a contact.                                     |
| `unidentified_by_date`| boolean | `true`               | Organize unidentified files into `YYYY-MM` subfolders. When `false`, all go directly under the type folder. |

**Example:**

```toml
[organization]
show_phone = false
group_suffix = "[group]"
unidentified_folder = "_Unknown"
unidentified_by_date = true
```

With `show_phone = false`, contact folders look like:

```
~/WhatsKeep/
├── John Smith/
│   └── Image/
└── Family Group [group]/
    └── Video/
```

---

### `[deduplication]`

Controls duplicate file detection and removal.

| Key         | Type    | Default    | Description                                                                                 |
| ----------- | ------- | ---------- | ------------------------------------------------------------------------------------------- |
| `enabled`   | boolean | `true`     | Enable deduplication. When a file already exists at the destination with identical content, the source file is deleted instead of moved. |
| `algorithm` | string  | `"sha256"` | Hash algorithm for comparing files. Options: `"sha256"`, `"md5"`, `"blake2b"`. SHA-256 is recommended for reliability. MD5 is faster but has known collision weaknesses. |

**How it works:** WhatsKeep first compares file sizes (different sizes means different content -- instant rejection). Only files with matching sizes are hashed and compared. Files are read in 8 MiB chunks, so large videos never load entirely into memory.

**Example:**

```toml
[deduplication]
enabled = true
algorithm = "blake2b"
```

---

### `[auto_update]`

Controls the automatic update mechanism.

| Key                    | Type    | Default    | Description                                                                     |
| ---------------------- | ------- | ---------- | ------------------------------------------------------------------------------- |
| `enabled`              | boolean | `true`     | Enable automatic update checks via the GitHub Releases API.                     |
| `channel`              | string  | `"stable"` | Update channel: `"stable"` for production releases, `"beta"` for pre-releases.  |
| `check_interval_hours` | integer | `24`       | Hours between update checks. The last check timestamp is stored locally.        |

**Example:**

```toml
[auto_update]
enabled = false
```

---

### `[notifications]`

Controls desktop notifications (platform-dependent).

| Key           | Type    | Default | Description                                          |
| ------------- | ------- | ------- | ---------------------------------------------------- |
| `enabled`     | boolean | `true`  | Master switch for all notifications.                 |
| `on_organize` | boolean | `false` | Notify after each successful organization run.       |
| `on_error`    | boolean | `true`  | Notify when an error occurs during organization.     |
| `on_update`   | boolean | `true`  | Notify when a new version is available.              |

**Example:**

```toml
[notifications]
enabled = true
on_organize = true
on_error = true
on_update = false
```

---

### `[logging]`

Controls log output and retention.

| Key              | Type    | Default  | Description                                                                   |
| ---------------- | ------- | -------- | ----------------------------------------------------------------------------- |
| `level`          | string  | `"INFO"` | Minimum log level. Options: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`. |
| `max_size_mb`    | integer | `10`     | Maximum log file size in megabytes before rotation.                           |
| `retention_days` | integer | `30`     | Number of days to keep old log files.                                         |

Log files are stored at `~/.whatskeep/whatskeep.log`. View them with:

```bash
whatskeep logs          # Last 50 lines
whatskeep logs --tail   # Follow in real-time
```

**Example:**

```toml
[logging]
level = "DEBUG"
max_size_mb = 50
retention_days = 90
```

---

## Default Configuration

If no `config.toml` exists, WhatsKeep uses these defaults:

```toml
[general]
language = "en"
download_dir = "auto"
backup_dir = "~/WhatsKeep"

[monitoring]
interval = 10
process_existing = true

[auto_update]
enabled = true
channel = "stable"
check_interval_hours = 24

[backup]
mode = "all"
allowlist = []
blocklist = []

[media_types]
image = true
audio = true
video = true
document = true
sticker = false
voice_note = true

[organization]
folder_template = "{contact}/{type}"
show_phone = true
group_suffix = "(group)"
unidentified_folder = "_Unidentified"
unidentified_by_date = true

[deduplication]
enabled = true
algorithm = "sha256"

[notifications]
enabled = true
on_organize = false
on_error = true
on_update = true

[logging]
level = "INFO"
max_size_mb = 10
retention_days = 30
```

## Configuration Validation

WhatsKeep validates your configuration on load. Invalid values produce clear error messages. You can also check validity explicitly:

```bash
whatskeep doctor
```

The doctor command includes a "Configuration valid" check that reports any issues found.

### Validated constraints

- `backup.mode` must be one of: `all`, `allowlist`, `blocklist`
- `logging.level` must be one of: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- `monitoring.interval` must be a positive number
- `auto_update.check_interval_hours` must be a positive number
- `auto_update.channel` must be one of: `stable`, `beta`
- `deduplication.algorithm` must be one of: `sha256`, `md5`, `blake2b`
- `logging.max_size_mb` must be a positive number
- `logging.retention_days` must be a positive number

Any option not explicitly set in your `config.toml` falls back to the default value. You only need to include the settings you want to change.
