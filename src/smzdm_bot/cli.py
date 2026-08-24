"""Command-line interface for SMZDM Bot.

Built with Typer for a beautiful CLI experience.

Usage:
    smzdm-bot run          Run tasks once
    smzdm-bot schedule     Run tasks on schedule
    smzdm-bot version      Show version
"""

import sys
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from smzdm_bot import __version__

# Initialize
app = typer.Typer(
    name="smzdm-bot",
    help="🛒 SMZDM Bot - 什么值得买每日签到",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()

# Log format
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
    "<level>{message}</level>"
)


def setup_logging(debug: bool = False, log_file: Path | None = None) -> None:
    """Configure logging."""
    logger.remove()

    # Console output
    level = "DEBUG" if debug else "INFO"
    logger.add(sys.stderr, format=LOG_FORMAT, level=level, colorize=True)

    # File output
    if log_file:
        logger.add(
            log_file,
            format=LOG_FORMAT,
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            compression="zip",
        )


def print_banner() -> None:
    """Print application banner."""
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]SMZDM Bot[/bold cyan] [dim]v{__version__}[/dim]\n"
            "[italic]什么值得买 · 每日签到[/italic]",
            border_style="cyan",
        )
    )
    console.print()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"smzdm-bot version [bold cyan]{__version__}[/bold cyan]")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version", "-v",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """🛒 SMZDM Bot - 什么值得买每日签到工具."""
    pass


@app.command()
def run(
    debug: Annotated[
        bool,
        typer.Option("--debug", "-d", help="Enable debug logging."),
    ] = False,
    log_file: Annotated[
        Path | None,
        typer.Option("--log-file", "-l", help="Log file path."),
    ] = None,
) -> None:
    """Run check-in tasks once.

    Examples:
        smzdm-bot run
        smzdm-bot run --debug
        smzdm-bot run --log-file ./smzdm.log
    """
    setup_logging(debug, log_file or Path("smzdm.log"))
    print_banner()

    from smzdm_bot.main import main as run_main

    exit_code = run_main()
    raise typer.Exit(exit_code)


@app.command()
def schedule(
    debug: Annotated[
        bool,
        typer.Option("--debug", "-d", help="Enable debug logging."),
    ] = False,
    log_file: Annotated[
        Path | None,
        typer.Option("--log-file", "-l", help="Log file path."),
    ] = None,
) -> None:
    """Run tasks on a schedule.

    The schedule time is determined by:
    - SMZDM_SCH_HOUR and SMZDM_SCH_MINUTE environment variables
    - Random time between 6-10 AM if not set

    Examples:
        smzdm-bot schedule
        SMZDM_SCH_HOUR=9 SMZDM_SCH_MINUTE=30 smzdm-bot schedule
    """
    setup_logging(debug, log_file or Path("smzdm.log"))
    print_banner()

    console.print("[bold green]Starting scheduler...[/bold green]")
    console.print("[dim]Press Ctrl+C to exit[/dim]\n")

    from smzdm_bot.scheduler import run_scheduler

    run_scheduler()


@app.command()
def config() -> None:
    """Show current configuration (without sensitive data)."""
    from smzdm_bot.config import get_settings
    from smzdm_bot.exceptions import ConfigurationError

    print_banner()

    try:
        settings = get_settings()
        users = settings.get_users()
        notify = settings.get_notify_config()
        scheduler = settings.get_scheduler_config()

        # Users table
        table = Table(title="👥 Users", show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Cookie", style="dim")
        table.add_column("SK", style="dim")

        for user in users:
            cookie_preview = user.cookie[:20] + "..." if len(user.cookie) > 20 else user.cookie
            sk_status = "✓" if user.sk else "✗"
            table.add_row(user.name, cookie_preview, sk_status)

        console.print(table)
        console.print()

        # Notification table
        table = Table(title="🔔 Notifications", show_header=True)
        table.add_column("Provider", style="cyan")
        table.add_column("Status")

        providers = [
            ("PushPlus", bool(notify.push_plus_token)),
            ("ServerChan", bool(notify.sc_key)),
            ("WeCom", bool(notify.wecom_webhook)),
            ("Telegram", bool(notify.tg_bot_token and notify.tg_user_id)),
        ]

        for name, enabled in providers:
            status = "[green]✓ Enabled[/green]" if enabled else "[dim]✗ Disabled[/dim]"
            table.add_row(name, status)

        console.print(table)
        console.print()

        # Scheduler info
        hour = scheduler.hour if scheduler.hour is not None else "random"
        minute = scheduler.minute if scheduler.minute is not None else "random"
        console.print(f"⏰ [bold]Schedule:[/bold] {hour}:{minute} ({scheduler.timezone})")

    except ConfigurationError as e:
        console.print(f"[red]Configuration error:[/red] {e.message}")
        raise typer.Exit(1) from None


# Entry points for pyproject.toml
def cli_entry() -> None:
    """CLI entry point."""
    app()


def scheduler_entry() -> None:
    """Scheduler entry point (shortcut)."""
    sys.argv = [sys.argv[0], "schedule"] + sys.argv[1:]
    app()


if __name__ == "__main__":
    app()
