# Setting Up WhatsApp Desktop on macOS

This guide walks through installing and configuring WhatsApp Desktop on macOS for use with WhatsKeep.

## Step 1: Install WhatsApp Desktop

You have two options:

### Option A: Mac App Store (Recommended)

1. Open the **App Store** on your Mac
2. Search for "WhatsApp Messenger"
3. Click **Get** and then **Install**
4. Open WhatsApp from your Applications folder or Launchpad

### Option B: Direct Download

1. Visit [whatsapp.com/download](https://www.whatsapp.com/download)
2. Download the macOS version
3. Open the `.dmg` file and drag WhatsApp to your Applications folder
4. Open WhatsApp from Applications

## Step 2: Sign In

1. Open WhatsApp Desktop
2. You will see a QR code on screen
3. On your phone, open WhatsApp > **Settings** > **Linked Devices** > **Link a Device**
4. Scan the QR code with your phone's camera
5. Wait for your chats to sync (this may take several minutes for large chat histories)

## Step 3: Enable Auto-Download

This is the most critical step. Without auto-download, WhatsApp will not save media files to your Mac.

1. In WhatsApp Desktop, click the **gear icon** (Settings) in the bottom-left corner
2. Click **Storage and Data**
3. Under **Media auto-download**, configure each type:
   - **Photos**: Set to **Always**
   - **Audio**: Set to **Always**
   - **Videos**: Set to **Always**
   - **Documents**: Set to **Always**

If you only want to organize certain media types, you can leave some set to "Wi-Fi" or "Never" -- but WhatsKeep can only organize files that are actually downloaded.

## Step 4: Verify Downloads

1. Send yourself a test image (e.g., send a photo to your own number via another device, or use the "Message Yourself" feature)
2. Wait a few seconds for it to download
3. Open **Finder** and navigate to `~/Downloads`
4. Look for a file named like: `WhatsApp Image 2026-04-08 at 14.20.43.jpeg`

If the file appears, WhatsApp Desktop is correctly configured.

## Step 5: Verify Database Access

WhatsKeep reads the WhatsApp database to identify which contact sent each file. Verify that it can access the database:

```bash
whatskeep doctor
```

Look for the line:
```
WhatsApp DB accessible    OK    /Users/you/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite
```

### If the database is not accessible

**Grant Full Disk Access to your terminal:**

On macOS Sonoma (14) and later, applications need explicit permission to read certain app containers.

1. Open **System Settings** > **Privacy & Security** > **Full Disk Access**
2. Click the **+** button
3. Navigate to and select your terminal application:
   - **Terminal.app**: `/Applications/Utilities/Terminal.app`
   - **iTerm2**: `/Applications/iTerm.app`
   - **Warp**: `/Applications/Warp.app`
   - **VS Code Terminal**: `/Applications/Visual Studio Code.app`
4. Enable the toggle for the added application
5. **Quit and reopen your terminal** (the permission change requires a restart)
6. Run `whatskeep doctor` again

### Database Location

The WhatsApp Desktop database on macOS is located at:

```
~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite
```

This is a SQLite database that WhatsApp maintains locally. WhatsKeep opens it in read-only mode and never modifies it. The database uses WAL (Write-Ahead Logging) mode, which allows WhatsKeep to read it even while WhatsApp Desktop is running.

## Step 6: Run WhatsKeep

With WhatsApp Desktop configured, you can now set up and run WhatsKeep:

```bash
# First-time setup
whatskeep init

# Organize existing files
whatskeep run

# Install the background daemon
whatskeep start
```

## macOS Daemon Details

When you run `whatskeep start`, WhatsKeep creates a launchd agent at:

```
~/Library/LaunchAgents/com.whatskeep.agent.plist
```

This agent:

- Starts automatically when you log in (`RunAtLoad: true`)
- Watches your Downloads folder for changes (`WatchPaths`)
- Throttles to run no more than once every 10 seconds
- Logs output to `~/.whatskeep/whatskeep.log`
- Logs errors to `~/.whatskeep/whatskeep.err`

### Managing the Daemon

```bash
# Check daemon status
whatskeep status

# Stop the daemon
whatskeep stop

# Restart the daemon
whatskeep stop && whatskeep start

# Remove the daemon entirely
whatskeep uninstall
```

### Manual launchctl Commands

If you need to troubleshoot at the launchd level:

```bash
# List loaded agents
launchctl list | grep whatskeep

# Manually load/unload
launchctl load ~/Library/LaunchAgents/com.whatskeep.agent.plist
launchctl unload ~/Library/LaunchAgents/com.whatskeep.agent.plist

# View the plist
cat ~/Library/LaunchAgents/com.whatskeep.agent.plist
```

## Troubleshooting

### "WhatsApp Desktop not found"

- Ensure you installed the native Desktop app, not just the web version at web.whatsapp.com
- If you installed via direct download, make sure WhatsApp is in `/Applications/`
- Open WhatsApp Desktop at least once and complete the sign-in process

### Files appear in Downloads but are not organized

- Run `whatskeep run --verbose` to see detailed processing logs
- Check that the filenames match the expected patterns (see [Troubleshooting](../troubleshooting.md))
- Verify media type filters in your configuration: `whatskeep config show`

### Database locked errors

WhatsApp Desktop keeps the database open while running. WhatsKeep handles this gracefully with retries, but in rare cases:

1. Close WhatsApp Desktop
2. Run `whatskeep run`
3. Reopen WhatsApp Desktop

This is usually only needed during initial setup or after a WhatsApp update.
