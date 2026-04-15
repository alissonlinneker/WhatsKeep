"""WhatsKeep CLI — Typer + Rich powered command-line interface."""

from __future__ import annotations

import contextlib
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from whatskeep import __app_name__, __version__

console = Console()

# ---------------------------------------------------------------------------
# App & config sub-app
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="whatskeep",
    help="Automatically organize and backup WhatsApp media by contact and group.",
    no_args_is_help=True,
)

config_app = typer.Typer(
    name="config",
    help="View, edit, or reset WhatsKeep configuration.",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_config_safe() -> dict:
    """Load config with graceful error handling."""
    from whatskeep.config import load_config

    try:
        return load_config()
    except Exception as exc:
        console.print(f"[red]Error loading config:[/red] {exc}")
        raise typer.Exit(1) from exc


def _get_log_path() -> Path:
    """Return the default log file path."""
    return Path.home() / ".whatskeep" / "whatskeep.log"


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

@app.command()
def init() -> None:
    """Interactive setup wizard — configure WhatsKeep for the first time."""
    from whatskeep.config import (
        DEFAULT_CONFIG,
        _dict_to_toml,
        save_default_config,
    )

    console.print(
        Panel(
            f"[bold cyan]{__app_name__}[/bold cyan] v{__version__} — Setup Wizard",
            expand=False,
        )
    )

    import copy

    config = copy.deepcopy(DEFAULT_CONFIG)

    # 1. Downloads folder
    default_dl = str(Path.home() / "Downloads")
    dl = Prompt.ask(
        "Downloads folder (where WhatsApp saves files)",
        default=default_dl,
    )
    config["general"] = {**config["general"], "download_dir": dl}

    # 2. Backup folder
    default_bk = str(Path.home() / "WhatsKeep")
    bk = Prompt.ask("Backup folder", default=default_bk)
    config["general"]["backup_dir"] = bk

    # 3. Backup mode
    mode = Prompt.ask(
        "Backup mode",
        choices=["all", "allowlist", "blocklist"],
        default="all",
    )
    config["backup"] = {**config["backup"], "mode": mode}

    # 4. Media types
    media_types: dict[str, bool] = {}
    for mtype in ("image", "audio", "video", "document", "sticker", "voice_note"):
        cur_default = config["media_types"].get(mtype, True)
        media_types[mtype] = Confirm.ask(
            f"  Enable [bold]{mtype}[/bold]?",
            default=cur_default,
        )
    config["media_types"] = media_types

    # 5. Daemon auto-start
    daemon_enabled = Confirm.ask("Start daemon on login?", default=True)
    # Store for later — daemon installation is separate
    _ = daemon_enabled

    # 6. Auto-update
    auto_update = Confirm.ask("Enable auto-updates?", default=True)
    config["auto_update"] = {**config["auto_update"], "enabled": auto_update}

    # Save
    path = save_default_config()
    # Overwrite with user choices
    path.write_text(_dict_to_toml(config), encoding="utf-8")

    # Summary table
    table = Table(title="Configuration Summary", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Downloads folder", dl)
    table.add_row("Backup folder", bk)
    table.add_row("Backup mode", mode)
    enabled_types = [k for k, v in media_types.items() if v]
    table.add_row("Media types", ", ".join(enabled_types))
    table.add_row("Auto-update", str(auto_update))
    table.add_row("Config path", str(path))
    console.print(table)

    console.print(
        "\n[green]Setup complete![/green] "
        "Run [bold]whatskeep run[/bold] to organize files."
    )


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

@app.command()
def run(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview changes without moving files.",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose/debug logging.",
    ),
    watch: bool = typer.Option(
        False, "--watch", "-w", help="Watch downloads folder continuously.",
    ),
) -> None:
    """Run organization once — scan downloads and move WhatsApp media."""
    from loguru import logger

    from whatskeep.organizer import Organizer

    # Configure loguru sink
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level, format="<level>{message}</level>")

    config = _load_config_safe()

    # Watch mode — continuous real-time monitoring
    if watch:
        from whatskeep.watcher import watch as watcher_watch

        # In watch mode, log to file for daemon compatibility
        log_path = Path.home() / ".whatskeep" / "watcher.log"
        logger.remove()
        logger.add(
            str(log_path),
            level=level,
            rotation="10 MB",
            retention="30 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}",
            enqueue=False,
        )
        if sys.stderr.isatty():
            logger.add(sys.stderr, level=level, format="<level>{message}</level>")
            console.print(
                Panel(
                    "[bold]Watching for WhatsApp files…[/bold] (Ctrl+C to stop)",
                    expand=False,
                )
            )
        watcher_watch(config=config)
        return

    organizer = Organizer(config)

    console.print(
        Panel("[bold]Running WhatsKeep organizer…[/bold]", expand=False)
    )

    try:
        result = organizer.run(dry_run=dry_run)
    except Exception as exc:
        console.print(f"[red]Organization failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        organizer.close()

    # Results table
    from whatskeep.utils.fs import get_file_size_human

    table = Table(title="Organization Results", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")
    table.add_row("Total files scanned", str(result.total_files))
    table.add_row("Organized", str(result.organized))
    table.add_row("Skipped", str(result.skipped))
    table.add_row("Duplicates removed", str(result.duplicates))
    table.add_row("Errors", str(result.errors))
    table.add_row("Data organized", get_file_size_human(result.bytes_organized))
    table.add_row("Space saved (dedup)", get_file_size_human(result.bytes_saved))
    console.print(table)

    if dry_run:
        console.print("[yellow]Dry-run — no files were moved.[/yellow]")

    if result.by_contact:
        ct = Table(title="By Contact", show_header=True)
        ct.add_column("Contact", style="cyan")
        ct.add_column("Files", style="green", justify="right")
        for name, count in sorted(
            result.by_contact.items(), key=lambda x: -x[1],
        ):
            ct.add_row(name, str(count))
        console.print(ct)

    if result.by_type:
        tt = Table(title="By Type", show_header=True)
        tt.add_column("Type", style="cyan")
        tt.add_column("Files", style="green", justify="right")
        for mtype, count in sorted(
            result.by_type.items(), key=lambda x: -x[1],
        ):
            tt.add_row(mtype, str(count))
        console.print(tt)

    if result.errors:
        console.print(f"\n[red]Errors ({result.errors}):[/red]")
        for err in result.error_details:
            console.print(f"  [dim]•[/dim] {err}")


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


@app.command()
def export(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview without copying files.",
    ),
) -> None:
    """Export ALL historical media from WhatsApp's internal storage.

    Copies (never moves) every media file from WhatsApp Desktop's database,
    organizing by contact/group. Safe to run multiple times — skips already exported files.
    """
    from whatskeep.organizer import Organizer
    from whatskeep.utils.fs import get_file_size_human

    config = _load_config_safe()
    organizer = Organizer(config)

    console.print(
        Panel(
            "[bold]Exporting all WhatsApp media…[/bold]\n"
            "This copies from WhatsApp's internal storage (never deletes originals).",
            expand=False,
        )
    )

    try:
        result = organizer.export_all(dry_run=dry_run)
    except Exception as exc:
        console.print(f"[red]Export failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        organizer.close()

    table = Table(title="Export Results", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")
    table.add_row("Total records in DB", str(result.total_files))
    table.add_row("Exported", str(result.organized))
    table.add_row("Skipped (existing/thumbs)", str(result.skipped))
    table.add_row("Errors", str(result.errors))
    table.add_row("Data exported", get_file_size_human(result.bytes_organized))
    console.print(table)

    if dry_run:
        console.print("[yellow]Dry-run — no files were copied.[/yellow]")

    if result.by_contact:
        ct = Table(title="Top Contacts", show_header=True)
        ct.add_column("Contact", style="cyan")
        ct.add_column("Files", style="green", justify="right")
        for name, count in sorted(
            result.by_contact.items(), key=lambda x: -x[1],
        )[:20]:
            ct.add_row(name, str(count))
        console.print(ct)


# ---------------------------------------------------------------------------
# evidence (subcommand group)
# ---------------------------------------------------------------------------

evidence_app = typer.Typer(
    name="evidence",
    help="Digital chain of custody — hash verification, evidence export, integrity checks.",
    no_args_is_help=True,
)
app.add_typer(evidence_app)


@evidence_app.command("status")
def evidence_status() -> None:
    """Show custody tracking statistics."""
    from whatskeep.evidence import CustodyManager

    config = _load_config_safe()
    backup_dir = Path(config["general"]["backup_dir"]).expanduser().resolve()
    mgr = CustodyManager(backup_dir)

    stats = mgr.get_custody_stats()
    mgr.close()

    table = Table(title="Evidence Custody Status", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")
    table.add_row("Files tracked", str(stats["total_tracked"]))
    table.add_row("With SHA-256 hash", str(stats["with_hash"]))
    table.add_row("Without hash (pending)", str(stats["without_hash"]))
    table.add_row("Deleted from chat", str(stats["deleted_from_chat"]))
    table.add_row("Custody events logged", str(stats["custody_events"]))
    table.add_row("Integrity checks run", str(stats["integrity_checks"]))
    table.add_row("Last integrity check", stats["last_check"] or "Never")
    console.print(table)


@evidence_app.command("verify")
def evidence_verify() -> None:
    """Re-check SHA-256 hashes of all tracked files to detect tampering."""
    from whatskeep.evidence import CustodyManager

    config = _load_config_safe()
    backup_dir = Path(config["general"]["backup_dir"]).expanduser().resolve()
    mgr = CustodyManager(backup_dir)

    console.print(Panel("[bold]Verifying file integrity…[/bold]", expand=False))
    results = mgr.verify_all()
    mgr.close()

    table = Table(title="Integrity Verification Results", show_header=True)
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right")
    table.add_row("[green]OK[/green]", str(results["ok"]))
    table.add_row("[red]Corrupted[/red]", str(results["corrupted"]))
    table.add_row("[yellow]Missing[/yellow]", str(results["missing"]))
    table.add_row("Total checked", str(results["total"]))
    console.print(table)

    if results["corrupted"]:
        console.print("\n[red bold]WARNING: Corrupted files detected![/red bold]")
        for d in results["details"]:
            console.print(f"  {d['file']}")
            console.print(f"    Expected: {d['expected']}")
            console.print(f"    Actual:   {d['actual']}")
    elif results["missing"]:
        console.print(
            f"\n[yellow]{results['missing']} file(s) missing from disk.[/yellow]"
        )
    else:
        console.print("\n[green]All files verified — integrity intact.[/green]")


@evidence_app.command("export")
def evidence_export(
    contact: str = typer.Option(
        None, "--contact", "-c", help="Export evidence for a specific contact only.",
    ),
    all_contacts: bool = typer.Option(
        False, "--all", help="Export complete evidence package.",
    ),
) -> None:
    """Export evidence package with manifest, hashes, and chain of custody log.

    Creates a structured folder ready to share with attorneys or present in court.
    """
    from whatskeep.evidence import CustodyManager

    if not contact and not all_contacts:
        console.print(
            "[yellow]Specify --contact 'Name' or --all[/yellow]\n"
            "Example: whatskeep evidence export --contact 'John Smith'\n"
            "Example: whatskeep evidence export --all"
        )
        return

    config = _load_config_safe()
    backup_dir = Path(config["general"]["backup_dir"]).expanduser().resolve()
    mgr = CustodyManager(backup_dir)

    console.print(Panel("[bold]Exporting evidence package…[/bold]", expand=False))
    pkg_dir = mgr.export_evidence(contact_name=contact)
    mgr.close()

    console.print(f"\n[green]Evidence package created:[/green] {pkg_dir}")
    console.print("\nContents:")
    for f in sorted(pkg_dir.iterdir()):
        size = f.stat().st_size if f.is_file() else 0
        icon = "dir" if f.is_dir() else f"{size:,} bytes"
        console.print(f"  {f.name} ({icon})")

    console.print(
        "\n[dim]DISCLAIMER: This package assists with evidence preservation "
        "but does NOT replace ata notarial or certified platforms.[/dim]"
    )


@evidence_app.command("hash")
def evidence_hash() -> None:
    """Generate SHA-256 hashes for all tracked files that don't have one yet."""
    from whatskeep.evidence import CustodyManager

    config = _load_config_safe()
    backup_dir = Path(config["general"]["backup_dir"]).expanduser().resolve()
    mgr = CustodyManager(backup_dir)

    stats = mgr.get_custody_stats()
    pending = stats["without_hash"]
    if pending == 0:
        console.print("[green]All tracked files already have hashes.[/green]")
        mgr.close()
        return

    console.print(f"Hashing {pending} files…")
    hashed = mgr.hash_pending_files()
    mgr.close()
    console.print(f"[green]{hashed} files hashed with SHA-256.[/green]")


# ---------------------------------------------------------------------------
# start / stop / status
# ---------------------------------------------------------------------------

@app.command()
def start() -> None:
    """Install and start the background daemon."""
    try:
        from whatskeep.platform import get_daemon_installer
    except ImportError as exc:
        console.print("[red]Platform daemon support is not available.[/red]")
        raise typer.Exit(1) from exc

    installer = get_daemon_installer()
    if installer is None:
        console.print(
            f"[red]No daemon installer for {platform.system()}.[/red]",
        )
        raise typer.Exit(1)

    try:
        installer.install()
        installer.start()
        console.print("[green]Daemon installed and started.[/green]")
    except Exception as exc:
        console.print(f"[red]Failed to start daemon:[/red] {exc}")
        raise typer.Exit(1) from exc


@app.command()
def stop() -> None:
    """Stop the background daemon."""
    try:
        from whatskeep.platform import get_daemon_installer
    except ImportError as exc:
        console.print("[red]Platform daemon support is not available.[/red]")
        raise typer.Exit(1) from exc

    installer = get_daemon_installer()
    if installer is None:
        console.print(
            f"[red]No daemon installer for {platform.system()}.[/red]",
        )
        raise typer.Exit(1)

    try:
        installer.stop()
        console.print("[green]Daemon stopped.[/green]")
    except Exception as exc:
        console.print(f"[red]Failed to stop daemon:[/red] {exc}")
        raise typer.Exit(1) from exc


@app.command()
def status() -> None:
    """Show daemon status and last run information."""
    try:
        from whatskeep.platform import get_daemon_installer
    except ImportError as exc:
        console.print("[red]Platform daemon support is not available.[/red]")
        raise typer.Exit(1) from exc

    installer = get_daemon_installer()
    if installer is None:
        console.print(
            f"[red]No daemon installer for {platform.system()}.[/red]",
        )
        raise typer.Exit(1)

    try:
        running = installer.is_running()
    except Exception:
        running = False

    status_label = (
        "[green]running[/green]" if running else "[yellow]stopped[/yellow]"
    )
    console.print(f"Daemon status: {status_label}")

    # Last run info from log
    log_path = _get_log_path()
    if log_path.exists():
        try:
            lines = log_path.read_text(encoding="utf-8").splitlines()
            if lines:
                console.print(f"Last log entry: [dim]{lines[-1]}[/dim]")
        except OSError:
            pass


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

@app.command()
def stats() -> None:
    """Show storage statistics for the backup directory."""
    from whatskeep.config import resolve_backup_dir
    from whatskeep.utils.fs import get_file_size_human
    from whatskeep.utils.stats import calculate_stats

    config = _load_config_safe()
    backup_dir = resolve_backup_dir(config)

    if not backup_dir.is_dir():
        console.print(
            f"[yellow]Backup directory does not exist:[/yellow] {backup_dir}",
        )
        raise typer.Exit(0)

    storage = calculate_stats(backup_dir)

    # Overview
    table = Table(title="Storage Statistics", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")
    table.add_row("Backup directory", str(backup_dir))
    table.add_row("Total files", str(storage.total_files))
    table.add_row("Total size", get_file_size_human(storage.total_bytes))
    console.print(table)

    # By contact
    if storage.by_contact:
        ct = Table(title="By Contact", show_header=True)
        ct.add_column("Contact", style="cyan")
        ct.add_column("Size", style="green", justify="right")
        for name, size in sorted(
            storage.by_contact.items(), key=lambda x: -x[1],
        ):
            ct.add_row(name, get_file_size_human(size))
        console.print(ct)

    # By type
    if storage.by_type:
        tt = Table(title="By Type", show_header=True)
        tt.add_column("Type", style="cyan")
        tt.add_column("Size", style="green", justify="right")
        for mtype, size in sorted(
            storage.by_type.items(), key=lambda x: -x[1],
        ):
            tt.add_row(mtype, get_file_size_human(size))
        console.print(tt)


# ---------------------------------------------------------------------------
# config subcommands
# ---------------------------------------------------------------------------

@config_app.command("show")
def config_show() -> None:
    """Print the current configuration as TOML."""
    from rich.text import Text

    from whatskeep.config import _dict_to_toml

    config = _load_config_safe()
    toml_text = _dict_to_toml(config)
    # Use Text to prevent Rich from interpreting TOML [section] as markup
    console.print(
        Panel(Text(toml_text), title="config.toml", border_style="cyan")
    )


@config_app.command("edit")
def config_edit() -> None:
    """Open the configuration file in your default editor."""
    from whatskeep.config import get_config_path, save_default_config

    path = get_config_path()
    if not path.exists():
        save_default_config(path)
        console.print(f"[dim]Created default config at {path}[/dim]")

    editor = os.environ.get(
        "EDITOR", "nano" if platform.system() != "Windows" else "notepad",
    )
    try:
        subprocess.run([editor, str(path)], check=True)
    except FileNotFoundError as exc:
        console.print(f"[red]Editor not found:[/red] {editor}")
        console.print(
            "Set the [bold]EDITOR[/bold] environment variable "
            f"or edit manually:\n  {path}"
        )
        raise typer.Exit(1) from exc
    except subprocess.CalledProcessError as exc:
        console.print(
            f"[red]Editor exited with error:[/red] {exc.returncode}",
        )
        raise typer.Exit(1) from exc


@config_app.command("reset")
def config_reset() -> None:
    """Reset configuration to defaults."""
    from whatskeep.config import get_config_path, save_default_config

    if not Confirm.ask(
        "[yellow]Reset configuration to defaults?[/yellow] "
        "This cannot be undone",
    ):
        console.print("Cancelled.")
        raise typer.Exit(0)

    path = get_config_path()
    save_default_config(path)
    console.print(
        f"[green]Configuration reset to defaults.[/green] ({path})",
    )


# ---------------------------------------------------------------------------
# contacts
# ---------------------------------------------------------------------------

@app.command()
def contacts(
    filter_text: str | None = typer.Option(
        None, "--filter", "-f", help="Filter contacts by name.",
    ),
) -> None:
    """List detected contacts and groups from the WhatsApp database."""
    from whatskeep.db import get_db_reader

    reader = get_db_reader()
    if reader is None or not reader.is_available():
        console.print(
            "[yellow]WhatsApp database is not accessible "
            "on this platform.[/yellow]",
        )
        raise typer.Exit(0)

    try:
        records = reader.get_media_records()
    except Exception as exc:
        console.print(f"[red]Error reading database:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        reader.close()

    # Deduplicate contacts
    seen: dict[str, tuple[str | None, bool]] = {}
    for rec in records:
        name = rec.contact_name
        if filter_text and filter_text.lower() not in name.lower():
            continue
        if name not in seen:
            seen[name] = (rec.phone, rec.is_group)

    if not seen:
        console.print("[yellow]No contacts found.[/yellow]")
        raise typer.Exit(0)

    table = Table(title="Contacts", show_header=True)
    table.add_column("#", style="dim", justify="right")
    table.add_column("Name", style="cyan")
    table.add_column("Phone", style="green")
    table.add_column("Type", style="magenta")

    for idx, (name, (phone, is_group)) in enumerate(
        sorted(seen.items(), key=lambda x: x[0].lower()), start=1,
    ):
        table.add_row(
            str(idx),
            name,
            phone or "\u2014",
            "Group" if is_group else "Contact",
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(seen)} contacts/groups[/dim]")


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

@app.command()
def update(
    check: bool = typer.Option(
        False, "--check", help="Only check for updates, don't install.",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force re-check ignoring cache interval.",
    ),
) -> None:
    """Check for updates and optionally auto-update."""
    try:
        from whatskeep.updater import check_for_update, perform_update, record_check
    except ImportError as exc:
        console.print(
            "[yellow]Auto-update module is not yet available.[/yellow]",
        )
        console.print(
            f"Current version: [bold]{__version__}[/bold]\n"
            "Check https://github.com/alissonlinneker/whatskeep"
            "/releases for updates."
        )
        raise typer.Exit(0) from exc

    if force:
        console.print("[dim]Forcing update check...[/dim]")

    info = check_for_update()
    record_check()

    if not info.is_newer:
        console.print(
            f"[green]You are on the latest version ({__version__}).[/green]",
        )
        return

    console.print(
        f"[cyan]Update available:[/cyan] "
        f"{__version__} \u2192 {info.latest_version}",
    )
    if info.changelog:
        console.print(f"\n{info.changelog}\n")

    if check:
        return

    if Confirm.ask("Install update now?", default=True):
        if perform_update(info):
            console.print(
                "[green]Update complete. "
                "Restart WhatsKeep to use the new version.[/green]",
            )
        else:
            console.print("[red]Update failed. Check logs for details.[/red]")


# ---------------------------------------------------------------------------
# logs
# ---------------------------------------------------------------------------

@app.command()
def logs(
    tail: bool = typer.Option(
        False, "--tail", "-t", help="Follow logs in real-time.",
    ),
) -> None:
    """Show recent log entries."""
    log_path = _get_log_path()

    if not log_path.exists():
        console.print("[yellow]No log file found.[/yellow]")
        console.print(f"[dim]Expected at: {log_path}[/dim]")
        raise typer.Exit(0)

    if tail:
        console.print(
            f"[dim]Tailing {log_path} \u2014 press Ctrl+C to stop[/dim]\n",
        )
        try:
            subprocess.run(["tail", "-f", str(log_path)], check=False)
        except KeyboardInterrupt:
            pass
        except FileNotFoundError:
            # Windows fallback: read and poll
            console.print(
                "[yellow]'tail' not available. "
                "Showing last 50 lines instead.[/yellow]",
            )
            _show_recent_logs(log_path, 50)
    else:
        _show_recent_logs(log_path, 50)


def _show_recent_logs(log_path: Path, num_lines: int) -> None:
    """Display the last *num_lines* from the log file."""
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        console.print(f"[red]Cannot read log file:[/red] {exc}")
        raise typer.Exit(1) from exc

    lines = text.splitlines()
    recent = lines[-num_lines:] if len(lines) > num_lines else lines

    if not recent:
        console.print("[dim]Log file is empty.[/dim]")
        return

    for line in recent:
        console.print(line)

    console.print(
        f"\n[dim]Showing last {len(recent)} of {len(lines)} "
        f"lines from {log_path}[/dim]",
    )


# ---------------------------------------------------------------------------
# uninstall
# ---------------------------------------------------------------------------

@app.command()
def uninstall() -> None:
    """Remove the daemon and optionally delete configuration."""
    if not Confirm.ask("[yellow]Uninstall WhatsKeep daemon?[/yellow]"):
        console.print("Cancelled.")
        raise typer.Exit(0)

    # Stop and remove daemon
    try:
        from whatskeep.platform import get_daemon_installer

        installer = get_daemon_installer()
        if installer is not None:
            with contextlib.suppress(Exception):
                installer.stop()
            try:
                installer.uninstall()
            except Exception as exc:
                console.print(
                    f"[yellow]Warning removing daemon:[/yellow] {exc}",
                )
            else:
                console.print("[green]Daemon removed.[/green]")
        else:
            console.print(
                "[dim]No daemon installer for this platform.[/dim]",
            )
    except ImportError:
        console.print(
            "[dim]Platform module not available "
            "\u2014 skipping daemon removal.[/dim]",
        )

    # Optionally remove config
    if Confirm.ask("Also delete configuration and logs?", default=False):
        config_dir = Path.home() / ".whatskeep"
        if config_dir.is_dir():
            shutil.rmtree(config_dir)
            console.print(f"[green]Removed {config_dir}[/green]")
        else:
            console.print(
                "[dim]No configuration directory found.[/dim]",
            )

    console.print("[green]Uninstall complete.[/green]")


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------

@app.command()
def version() -> None:
    """Show version and platform information."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("WhatsKeep", __version__)
    table.add_row("Python", platform.python_version())
    table.add_row("Platform", platform.platform())
    table.add_row("Architecture", platform.machine())
    console.print(table)


@app.command()
def tray() -> None:
    """Launch WhatsKeep as a system tray application (no terminal needed)."""
    from whatskeep.tray import run_tray

    run_tray()


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

@app.command()
def doctor() -> None:
    """Diagnose common issues with your WhatsKeep setup."""
    console.print(
        Panel(
            "[bold]WhatsKeep Doctor[/bold] \u2014 Checking your setup\u2026",
            expand=False,
        )
    )

    checks: list[tuple[str, bool, str]] = []

    # 1. Python version
    py_ver = sys.version_info
    py_ok = py_ver >= (3, 10)
    checks.append((
        "Python >= 3.10",
        py_ok,
        f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}",
    ))

    # 2. Platform
    sys_name = platform.system()
    checks.append((
        "Platform supported",
        sys_name in ("Darwin", "Windows", "Linux"),
        sys_name,
    ))

    # 3. WhatsApp Desktop / DB
    from whatskeep.db import get_db_reader

    reader = get_db_reader()
    db_available = False
    db_detail = "not found"
    if reader is not None:
        db_available = reader.is_available()
        db_path = reader.db_path()
        db_detail = str(db_path) if db_path else "path unknown"
        if not db_available:
            db_detail += " (not readable)"
        reader.close()
    checks.append(("WhatsApp DB accessible", db_available, db_detail))

    # 4. Downloads folder
    from whatskeep.config import (
        load_config,
        resolve_backup_dir,
        resolve_download_dir,
        validate_config,
    )

    try:
        config = load_config()
    except Exception:
        config = {}

    dl_dir = resolve_download_dir(config)
    dl_exists = dl_dir.is_dir()
    checks.append(("Downloads folder exists", dl_exists, str(dl_dir)))

    # 5. Backup folder
    bk_dir = resolve_backup_dir(config)
    bk_exists = bk_dir.is_dir()
    checks.append(("Backup folder exists", bk_exists, str(bk_dir)))

    # 6. Daemon status
    try:
        from whatskeep.platform import get_daemon_installer

        installer = get_daemon_installer()
        if installer is not None:
            daemon_running = installer.is_running()
            checks.append(("Daemon running", daemon_running, ""))
        else:
            checks.append((
                "Daemon installer",
                False,
                "not available for this platform",
            ))
    except (ImportError, Exception):
        checks.append(("Daemon installer", False, "module not available"))

    # 7. Config valid
    errors = validate_config(config)
    checks.append((
        "Configuration valid",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    ))

    # 8. Disk space
    try:
        check_path = bk_dir.parent if bk_dir.parent.exists() else Path.home()
        usage = shutil.disk_usage(str(check_path))
        free_gb = usage.free / (1024**3)
        disk_ok = free_gb > 1.0
        checks.append((
            "Disk space (> 1 GB free)",
            disk_ok,
            f"{free_gb:.1f} GB free",
        ))
    except OSError:
        checks.append(("Disk space", False, "unable to check"))

    # Render
    table = Table(title="Diagnostic Results", show_header=True)
    table.add_column("Check", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    for name, ok, detail in checks:
        icon = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
        table.add_row(name, icon, detail)

    console.print(table)

    failed = sum(1 for _, ok, _ in checks if not ok)
    if failed:
        console.print(
            f"\n[yellow]{failed} issue(s) found.[/yellow] "
            "Fix them and run [bold]whatskeep doctor[/bold] again.",
        )
    else:
        console.print("\n[green]All checks passed![/green]")
