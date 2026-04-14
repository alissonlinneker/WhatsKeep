# Setting Up WhatsApp Desktop on Windows

This guide walks through installing and configuring WhatsApp Desktop on Windows for use with WhatsKeep.

## Step 1: Install WhatsApp Desktop

You have two options:

### Option A: Microsoft Store (Recommended)

1. Open the **Microsoft Store** on your PC
2. Search for "WhatsApp"
3. Click **Get** or **Install**
4. Once installed, open WhatsApp from the Start menu

### Option B: Direct Download

1. Visit [whatsapp.com/download](https://www.whatsapp.com/download)
2. Download the Windows version (64-bit)
3. Run the installer and follow the on-screen prompts
4. Open WhatsApp from the Start menu or desktop shortcut

## Step 2: Sign In

1. Open WhatsApp Desktop
2. A QR code will be displayed on screen
3. On your phone, open WhatsApp > **Settings** > **Linked Devices** > **Link a Device**
4. Scan the QR code with your phone's camera
5. Wait for your chats to sync (this may take several minutes for large chat histories)

## Step 3: Enable Auto-Download

This is the most critical step. Without auto-download, WhatsApp will not save media files to your PC.

1. In WhatsApp Desktop, click the **gear icon** (Settings) in the bottom-left corner
2. Click **Storage and Data**
3. Under **Media auto-download**, configure each type:
   - **Photos**: Set to **Always**
   - **Audio**: Set to **Always**
   - **Videos**: Set to **Always**
   - **Documents**: Set to **Always**

If you only want to organize certain media types, you can leave some disabled -- but WhatsKeep can only organize files that are actually downloaded.

## Step 4: Verify Downloads

1. Send yourself a test image (e.g., via another device or the "Message Yourself" feature)
2. Wait a few seconds for it to download
3. Open **File Explorer** and navigate to your Downloads folder:
   ```
   %USERPROFILE%\Downloads
   ```
   Or simply press `Win + E` and click "Downloads" in the sidebar.
4. Look for a file named like: `WhatsApp Image 2026-04-08 at 14.20.43.jpeg`

If the file appears, WhatsApp Desktop is correctly configured.

## Step 5: Verify Database Access

WhatsKeep reads the WhatsApp database to identify which contact sent each file. Verify database access:

```cmd
whatskeep doctor
```

Look for the line:
```
WhatsApp DB accessible    OK
```

### Database Location

When installed from the Microsoft Store, the WhatsApp database is typically located at:

```
%LocalAppData%\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm\LocalState\shared\ChatStorage.sqlite
```

For the direct-download version, the path may vary. WhatsKeep attempts to locate the database automatically.

### If the database is not accessible

1. **Ensure WhatsApp Desktop has synced.** Open WhatsApp Desktop and wait for all chats to load completely. The database is only populated after sync.

2. **Run from the same user account.** The database is stored in a per-user directory. Running WhatsKeep from a different Windows user account will not find it.

3. **Check Windows permissions.** Some antivirus or security software may restrict access to app data directories. Add an exception for WhatsKeep if needed.

## Step 6: Run WhatsKeep

With WhatsApp Desktop configured, set up and run WhatsKeep:

```cmd
:: First-time setup
whatskeep init

:: Organize existing files
whatskeep run

:: Install the background task
whatskeep start
```

## Windows Daemon Details

When you run `whatskeep start`, WhatsKeep creates a Windows Scheduled Task named "WhatsKeep" with these properties:

- **Trigger**: Runs on user logon
- **Repeat interval**: Every 1 minute
- **Duration**: Indefinite (runs continuously while logged in)
- **Action**: Executes `whatskeep run`

### Managing the Daemon

```cmd
:: Check daemon status
whatskeep status

:: Stop the daemon
whatskeep stop

:: Restart the daemon
whatskeep stop
whatskeep start

:: Remove the daemon entirely
whatskeep uninstall
```

### Manual Task Scheduler Commands

If you need to troubleshoot at the Task Scheduler level:

```cmd
:: View task details
schtasks /query /tn WhatsKeep /fo LIST /v

:: Manually run the task
schtasks /run /tn WhatsKeep

:: End the running task
schtasks /end /tn WhatsKeep

:: Delete the task
schtasks /delete /tn WhatsKeep /f
```

You can also manage the task through the graphical **Task Scheduler** application:

1. Press `Win + R`, type `taskschd.msc`, and press Enter
2. In the left panel, click **Task Scheduler Library**
3. Find "WhatsKeep" in the list
4. Right-click for options (Run, End, Disable, Delete, Properties)

## Path Considerations

WhatsKeep must be accessible from the system PATH for the scheduled task to work. If you installed WhatsKeep in a virtual environment, the task may fail because the environment is not activated in the scheduled context.

**Recommended:** Install WhatsKeep system-wide:

```cmd
pip install whatskeep
```

If you need to use a virtual environment, update the task manually to point to the full path of the `whatskeep` executable within the venv:

```cmd
schtasks /change /tn WhatsKeep /tr "C:\path\to\venv\Scripts\whatskeep.exe run"
```

## Troubleshooting

### "WhatsApp Desktop not found"

- Ensure you installed the native Desktop app, not just the web version at web.whatsapp.com
- Open WhatsApp Desktop at least once and complete the sign-in process
- If using the Microsoft Store version, ensure the Store app is up to date

### Task creation requires administrator privileges

If `whatskeep start` fails with a permissions error:

1. Open **Command Prompt** or **PowerShell** as Administrator (right-click > "Run as administrator")
2. Run `whatskeep start` from the elevated prompt
3. Subsequent runs of `whatskeep run` do not require elevation

### Files appear in Downloads but are not organized

- Run `whatskeep run --verbose` to see detailed processing logs
- Check that the filenames match the expected patterns
- Verify media type filters: `whatskeep config show`

### Windows Defender or antivirus interference

Some security software may flag or block WhatsKeep's file operations. If files are not being moved:

1. Check your antivirus quarantine for WhatsKeep-related events
2. Add `~/.whatskeep/` and `~/WhatsKeep/` to your antivirus exclusion list
3. Add the `whatskeep` executable to the allowed programs list
