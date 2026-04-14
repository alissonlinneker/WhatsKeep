# Setting Up WhatsApp Desktop on Linux

This guide covers installing and configuring WhatsApp Desktop on Linux for use with WhatsKeep.

## Important Note About Linux Support

WhatsApp does not provide an official native Linux Desktop application. There are several community-maintained options and workarounds. Database support on Linux is best-effort -- WhatsKeep can organize files by type and date even without database access, but contact identification may be limited.

## Step 1: Install a WhatsApp Desktop Client

### Option A: WhatsApp for Linux (Unofficial, Recommended)

The most popular unofficial client that provides a native-like experience:

**Via Snap:**
```bash
sudo snap install whatsapp-for-linux
```

**Via Flatpak:**
```bash
flatpak install flathub com.github.nickvergessen.whatsapp-for-linux
```

### Option B: Official WhatsApp Beta (If Available)

WhatsApp occasionally releases beta versions for Linux. Check [whatsapp.com/download](https://www.whatsapp.com/download) for availability.

### Option C: nativefier or Electron Wrapper

You can create a desktop wrapper around WhatsApp Web:

```bash
npx nativefier --name "WhatsApp" "https://web.whatsapp.com"
```

Note: This approach does not create a local database, so contact identification will not be available. Files will still be organized by type and date.

## Step 2: Sign In

1. Open the WhatsApp Desktop client
2. A QR code will be displayed
3. On your phone, open WhatsApp > **Settings** > **Linked Devices** > **Link a Device**
4. Scan the QR code with your phone's camera
5. Wait for your chats to sync

## Step 3: Enable Auto-Download

1. In the WhatsApp client, navigate to **Settings** > **Storage and Data**
2. Under **Media auto-download**, enable all types:
   - **Photos**: Set to **Always**
   - **Audio**: Set to **Always**
   - **Videos**: Set to **Always**
   - **Documents**: Set to **Always**

Note: The settings interface may vary depending on which client you installed.

## Step 4: Verify Downloads

1. Send yourself a test image
2. Wait for it to download
3. Check your Downloads folder:
   ```bash
   ls ~/Downloads/WhatsApp*
   ```
4. You should see a file like: `WhatsApp Image 2026-04-08 at 14.20.43.jpeg`

### Custom Download Directory

If your client saves files to a non-standard location, configure WhatsKeep to look there:

```bash
whatskeep config edit
```

Set the `download_dir` under `[general]`:

```toml
[general]
download_dir = "/home/you/custom-downloads"
```

WhatsKeep respects the `XDG_DOWNLOAD_DIR` environment variable when `download_dir` is set to `"auto"`. If you have this set in `~/.config/user-dirs.dirs`, WhatsKeep will find it automatically.

## Step 5: Verify Database Access

```bash
whatskeep doctor
```

### Database Paths by Client

The database location depends on which client you installed:

| Client                    | Typical Database Path                                                    |
| ------------------------- | ------------------------------------------------------------------------ |
| WhatsApp for Linux (snap) | `~/snap/whatsapp-for-linux/current/.config/WhatsApp/` (varies)          |
| WhatsApp for Linux (flatpak) | `~/.var/app/com.github.nickvergessen.whatsapp-for-linux/` (varies)   |
| Official beta (if available) | `~/.config/WhatsApp/` or similar                                      |
| nativefier/Electron wrapper  | No local database (web-based)                                         |

### If the database is not accessible

This is common on Linux. WhatsKeep will still function -- it just organizes files into the `_Unidentified` folder by type and date instead of by contact.

To get the most out of WhatsKeep on Linux:

1. Use a client that maintains a local SQLite database
2. Check if the database exists at any of the paths above
3. If found, verify read permissions:
   ```bash
   ls -la /path/to/ChatStorage.sqlite
   ```

## Step 6: Run WhatsKeep

```bash
# First-time setup
whatskeep init

# Organize existing files
whatskeep run

# Install the background daemon
whatskeep start
```

## Linux Daemon Details

When you run `whatskeep start`, WhatsKeep creates a systemd user service at:

```
~/.config/systemd/user/whatskeep.service
```

The service unit file looks like:

```ini
[Unit]
Description=WhatsKeep -- WhatsApp media organizer
After=default.target

[Service]
Type=simple
ExecStart=/path/to/whatskeep run --watch
Restart=on-failure
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
```

The service:

- Runs as your user (not root)
- Starts automatically when you log in
- Restarts on failure after 10 seconds
- Watches the Downloads folder for new files in real-time

### Managing the Daemon

```bash
# Check daemon status
whatskeep status

# Or use systemctl directly for more detail
systemctl --user status whatskeep

# Stop the daemon
whatskeep stop

# Restart
whatskeep stop && whatskeep start

# View logs via journalctl
journalctl --user -u whatskeep -f

# Remove the daemon entirely
whatskeep uninstall
```

### Enabling Lingering

By default, systemd user services only run while you are logged in. If you want WhatsKeep to run even after you log out (e.g., on a headless server or always-on desktop):

```bash
loginctl enable-linger $USER
```

This allows your user services to persist across sessions.

### Manual systemd Commands

```bash
# Reload unit files after changes
systemctl --user daemon-reload

# Enable the service (auto-start on login)
systemctl --user enable whatskeep

# Disable auto-start
systemctl --user disable whatskeep

# View recent logs
journalctl --user -u whatskeep -n 100

# Follow logs in real-time
journalctl --user -u whatskeep -f
```

## Troubleshooting

### Daemon fails to start

1. Check the service status:
   ```bash
   systemctl --user status whatskeep
   ```

2. View logs for errors:
   ```bash
   journalctl --user -u whatskeep -n 50
   ```

3. Ensure the `whatskeep` executable is in your PATH. If installed in a virtual environment, the service may not find it. Either install system-wide or edit the unit file to use the full path:
   ```bash
   systemctl --user edit whatskeep
   ```
   Add:
   ```ini
   [Service]
   ExecStart=
   ExecStart=/home/you/.local/bin/whatskeep run --watch
   ```

### snap/flatpak sandbox restrictions

Snap and Flatpak applications run in sandboxed environments. This can affect:

- **File access**: The client may save downloads to a sandboxed directory instead of `~/Downloads`. Check the client's settings to see where files are saved.
- **Database access**: WhatsKeep (running outside the sandbox) may not be able to read the sandboxed database.

**Workaround for file access:**

Find where the client saves downloads:
```bash
find ~/snap -name "WhatsApp*" -type f 2>/dev/null
find ~/.var -name "WhatsApp*" -type f 2>/dev/null
```

Then set `download_dir` in your WhatsKeep config to point to that location.

### XDG directories

WhatsKeep follows the XDG Base Directory Specification when `download_dir` is set to `"auto"`. If your Downloads folder is not at `~/Downloads`, set the `XDG_DOWNLOAD_DIR` environment variable or configure the path explicitly in `config.toml`.

### SELinux or AppArmor restrictions

On distributions with mandatory access control (Fedora, Ubuntu), WhatsKeep's file operations may be restricted. If files are not being moved:

1. Check the audit log:
   ```bash
   sudo ausearch -m AVC -ts recent    # SELinux
   sudo dmesg | grep apparmor          # AppArmor
   ```

2. If WhatsKeep is being blocked, you may need to create a policy exception. This is distribution-specific -- consult your distribution's documentation.

### No systemd (init.d or other init systems)

If your system does not use systemd:

1. `whatskeep start` will report that no daemon installer is available
2. You can run WhatsKeep manually via cron:
   ```bash
   crontab -e
   ```
   Add:
   ```
   */5 * * * * /path/to/whatskeep run >> ~/.whatskeep/whatskeep.log 2>&1
   ```
   This runs WhatsKeep every 5 minutes.

3. Alternatively, run it as a background process:
   ```bash
   nohup whatskeep run --watch > ~/.whatskeep/whatskeep.log 2>&1 &
   ```
