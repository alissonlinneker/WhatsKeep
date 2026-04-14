# Troubleshooting

This guide covers common issues with WhatsKeep and how to resolve them. Start by running the built-in diagnostics:

```bash
whatskeep doctor
```

This command checks Python version, platform support, WhatsApp database accessibility, folder existence, daemon status, configuration validity, and disk space. Fix any items marked `FAIL` before proceeding.

---

## WhatsApp Database Not Found

**Symptom:** `whatskeep doctor` shows "WhatsApp DB accessible: FAIL", or `whatskeep contacts` reports "WhatsApp database is not accessible on this platform."

**Cause:** WhatsKeep cannot locate or read the WhatsApp Desktop local database.

### Solutions

#### macOS

1. **Confirm WhatsApp Desktop is installed.** The database is created by WhatsApp Desktop (not the web version). Install it from the [App Store](https://apps.apple.com/app/whatsapp-messenger/id310633997) or [whatsapp.com/download](https://www.whatsapp.com/download).

2. **Confirm the database exists.** Check for the file at:
   ```
   ~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite
   ```
   If this path does not exist, open WhatsApp Desktop, sign in, and wait for your chat history to sync.

3. **Grant Full Disk Access.** On macOS Sonoma and later, terminal applications may need Full Disk Access to read the WhatsApp container:
   - Open **System Settings** > **Privacy & Security** > **Full Disk Access**
   - Add your terminal application (Terminal.app, iTerm2, etc.)
   - Restart the terminal and try again

4. **Database locked.** If WhatsApp Desktop is running and actively writing, the database may be temporarily locked. WhatsKeep retries up to 3 times with exponential backoff. If it still fails, try closing WhatsApp Desktop, running `whatskeep run`, and then reopening it.

#### Windows

1. **Confirm WhatsApp Desktop is installed** from the [Microsoft Store](https://apps.microsoft.com/detail/whatsapp/9NKSQGP7F2NH) or [whatsapp.com/download](https://www.whatsapp.com/download).

2. **Check the database path:**
   ```
   %LocalAppData%\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm\LocalState\shared\ChatStorage.sqlite
   ```

3. **Run from the same user account** that installed WhatsApp Desktop. The database is user-specific.

#### Linux

1. WhatsApp does not have an official Linux Desktop client. Database support is best-effort.
2. If using an unofficial client (WhatsApp for Linux via snap/flatpak), the database path varies. WhatsKeep may not be able to locate it automatically.
3. Without DB access, WhatsKeep still organizes files -- they go into the `_Unidentified` folder sorted by type and date.

---

## Permission Errors

**Symptom:** Errors like "Permission denied" when reading the Downloads folder or writing to the backup directory.

### Solutions

1. **Check folder permissions:**
   ```bash
   ls -la ~/Downloads
   ls -la ~/WhatsKeep
   ```
   Your user must have read access to the Downloads folder and write access to the backup directory.

2. **macOS Full Disk Access.** If WhatsKeep is run as a daemon (launchd agent), the agent inherits the permissions of the launching user. Ensure your terminal has Full Disk Access (see above).

3. **Custom download/backup paths.** If you configured a custom `download_dir` or `backup_dir` in `config.toml`, verify the paths exist and are accessible:
   ```bash
   whatskeep config show
   ```

4. **Create the backup directory manually** if it does not exist:
   ```bash
   mkdir -p ~/WhatsKeep
   ```
   WhatsKeep creates it automatically on the first run, but if there is a parent directory permission issue, manual creation may help isolate the problem.

---

## Files Not Being Detected

**Symptom:** WhatsApp media files are in your Downloads folder, but `whatskeep run` reports 0 files scanned.

### Solutions

1. **Verify the filename pattern.** WhatsKeep detects files matching these patterns:
   - `WhatsApp Image 2026-04-08 at 14.20.43.jpeg` (modern Desktop format)
   - `WhatsApp-Image-2026-04-08-at-14.20.43.jpeg` (hyphen variant)
   - `WhatsApp_Image_2026-04-08_at_14.20.43.jpeg` (underscore variant)
   - `IMG-20260408-WA0032.jpg` (legacy Android format)
   - `WhatsApp Chat - Contact Name.zip` (chat exports)

   If your files have a different naming pattern, they will not be recognized. This can happen with third-party WhatsApp clients or manual renames.

2. **Check your Downloads folder path.**
   ```bash
   whatskeep config show
   ```
   If `download_dir = "auto"`, WhatsKeep looks at `~/Downloads`. If WhatsApp saves to a different folder, set the correct path:
   ```bash
   whatskeep config edit
   ```

3. **Check media type filters.** If you disabled certain media types in configuration, those files are skipped:
   ```bash
   whatskeep config show
   ```
   Look at the `[media_types]` section. Ensure the relevant types are set to `true`.

4. **Enable WhatsApp auto-download.** In WhatsApp Desktop: **Settings** > **Storage and Data** > enable auto-download for all media types. Without this, WhatsApp does not save files to your Downloads folder. See [Setup WhatsApp](setup-whatsapp/) for detailed instructions.

5. **Run with verbose logging** to see what WhatsKeep is doing:
   ```bash
   whatskeep run --verbose
   ```

---

## Daemon Not Starting

**Symptom:** `whatskeep start` fails, or `whatskeep status` shows "stopped" after starting.

### macOS (launchd)

1. **Check if the agent is loaded:**
   ```bash
   launchctl list | grep whatskeep
   ```

2. **View agent errors:**
   ```bash
   cat ~/.whatskeep/whatskeep.err
   ```

3. **Unload and reload:**
   ```bash
   whatskeep stop
   whatskeep start
   ```

4. **Verify the plist:**
   ```bash
   cat ~/Library/LaunchAgents/com.whatskeep.agent.plist
   ```
   Ensure `ProgramArguments` points to a valid `whatskeep` executable.

5. **Check if the executable is in PATH.** The daemon runs outside your shell, so it may not find `whatskeep` if it was installed in a virtual environment. Install system-wide with:
   ```bash
   pip install whatskeep
   ```

### Windows (Task Scheduler)

1. **Check task status:**
   ```cmd
   schtasks /query /tn WhatsKeep /fo LIST /v
   ```

2. **Run as administrator** if task creation fails due to permissions.

3. **Verify the executable path** in the task configuration.

### Linux (systemd)

1. **Check service status:**
   ```bash
   systemctl --user status whatskeep
   ```

2. **View logs:**
   ```bash
   journalctl --user -u whatskeep -n 50
   ```

3. **Reload and restart:**
   ```bash
   systemctl --user daemon-reload
   systemctl --user restart whatskeep
   ```

4. **Enable lingering** if the service stops when you log out:
   ```bash
   loginctl enable-linger $USER
   ```

---

## Running `whatskeep doctor`

The `doctor` command performs these checks:

| Check                  | What it verifies                                                        |
| ---------------------- | ----------------------------------------------------------------------- |
| Python >= 3.10         | Python version meets the minimum requirement                            |
| Platform supported     | Operating system is macOS, Windows, or Linux                            |
| WhatsApp DB accessible | The WhatsApp database file exists and is readable                       |
| Downloads folder exists| The configured downloads directory is present                           |
| Backup folder exists   | The configured backup directory is present                              |
| Daemon running         | The background daemon is active                                         |
| Configuration valid    | The `config.toml` has no invalid values                                 |
| Disk space (> 1 GB)    | At least 1 GB of free space on the backup drive                         |

**Example output:**

```
WhatsKeep Doctor -- Checking your setup...

  Check                     Status   Details
  Python >= 3.10            OK       3.13.2
  Platform supported        OK       Darwin
  WhatsApp DB accessible    OK       /Users/you/Library/Group Containers/.../ChatStorage.sqlite
  Downloads folder exists   OK       /Users/you/Downloads
  Backup folder exists      OK       /Users/you/WhatsKeep
  Daemon running            OK
  Configuration valid       OK
  Disk space (> 1 GB free)  OK       48.2 GB free

All checks passed!
```

---

## Contact Identification Rate Is Low

**Symptom:** Most files end up in `_Unidentified` despite having a working database.

### Solutions

1. **Ensure auto-download is enabled** in WhatsApp Desktop. Without it, the database records may not have the media entries WhatsKeep uses for correlation.

2. **Timing tolerance.** WhatsKeep matches files to database records using a +/-3 second window around the file's timestamp. If your system clock was significantly off when the files were created, matches may fail.

3. **Legacy filenames have no time-of-day.** Android-format filenames like `IMG-20260408-WA0032.jpg` only contain a date (no hours/minutes/seconds), making precise matching impossible. These files will typically end up in `_Unidentified`.

4. **Database sync.** If you recently installed WhatsApp Desktop, the database may not have historical records for older media. Only media received after the Desktop app was set up will have database entries.

---

## Deduplication Questions

**Q: Will WhatsKeep delete my original files?**

When deduplication is enabled and a file at the destination is an exact byte-for-byte match (verified via SHA-256 hash), the source file in Downloads is deleted. The copy in your backup directory is preserved. If the files differ in content, both are kept (the new file gets a counter suffix like `(1)`).

**Q: What if I want to keep duplicates?**

Disable deduplication in your configuration:

```toml
[deduplication]
enabled = false
```

**Q: Is MD5 safe for deduplication?**

While MD5 has known collision vulnerabilities for security purposes, accidental collisions between real media files are effectively impossible. SHA-256 (the default) provides a stronger guarantee with negligible performance difference for typical file sizes.

---

## Logs and Debugging

WhatsKeep logs to `~/.whatskeep/whatskeep.log`. To investigate issues:

```bash
# View recent logs
whatskeep logs

# Follow logs in real-time (macOS/Linux)
whatskeep logs --tail

# Run with maximum verbosity
whatskeep run --verbose
```

Set the log level to `DEBUG` for the most detailed output:

```toml
[logging]
level = "DEBUG"
```

---

## Uninstalling WhatsKeep

To completely remove WhatsKeep:

```bash
# Remove daemon and optionally delete config/logs
whatskeep uninstall

# Uninstall the package
pip uninstall whatskeep
```

The `whatskeep uninstall` command stops the daemon, removes the daemon configuration (launchd plist, scheduled task, or systemd unit), and optionally deletes `~/.whatskeep/` (configuration and logs). Your organized media in `~/WhatsKeep/` is never touched.

---

## Getting Help

If your issue is not covered here:

1. Run `whatskeep doctor` and include the output
2. Run `whatskeep run --verbose` and include the log output
3. Open an issue at [github.com/alissonlinneker/whatskeep/issues](https://github.com/alissonlinneker/whatskeep/issues)
