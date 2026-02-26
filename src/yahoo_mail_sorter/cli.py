"""CLI composition root — Typer commands for scan, sort, clean, folders."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from yahoo_mail_sorter.classifier import Classifier
from yahoo_mail_sorter.config import load_config
from yahoo_mail_sorter.exceptions import YahooMailSorterError
from yahoo_mail_sorter.imap_client import IMAPClient
from yahoo_mail_sorter.models import Category, SortReport
from yahoo_mail_sorter.rules_loader import load_rules
from yahoo_mail_sorter.sorter import Sorter

app = typer.Typer(
    name="yahoo-mail-sorter",
    help="Classify and sort Yahoo Japan Mail via IMAP.",
    no_args_is_help=True,
)
console = Console()


def _setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )


def _build_sorter(env_file: Path | None, rules_file: Path | None) -> tuple[Sorter, IMAPClient]:
    """Wire up dependencies and return (sorter, imap_client)."""
    config = load_config(env_path=env_file)
    rules_path = rules_file or config.rules_path
    categories = load_rules(rules_path)
    classifier = Classifier(categories)
    imap = IMAPClient(config.imap)
    return Sorter(imap, classifier), imap


def _print_report(report: SortReport, *, dry_run: bool) -> None:
    """Render a sort report as a rich table."""
    mode = "[yellow]DRY RUN[/yellow]" if dry_run else "[green]EXECUTED[/green]"
    console.print(f"\n{mode} — {report.total} emails processed\n")

    if not report.by_category:
        console.print("[dim]No emails found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Sample Subject")

    for category in Category:
        items = report.by_category.get(category, [])
        if not items:
            continue
        sample = items[0].email.subject[:60]
        table.add_row(category.value, str(len(items)), sample)

    console.print(table)

    if dry_run:
        console.print("\n[yellow]Pass --execute to actually move emails.[/yellow]")
    else:
        console.print(f"\n[green]Moved {report.moved} emails.[/green]")


# Common options
EnvFileOpt = Annotated[
    Path | None,
    typer.Option("--env-file", help="Path to .env file"),
]
RulesFileOpt = Annotated[
    Path | None,
    typer.Option("--rules-file", help="Path to rules.yaml"),
]
LimitOpt = Annotated[
    int | None,
    typer.Option("--limit", "-n", help="Max emails to process"),
]
DebugOpt = Annotated[
    bool,
    typer.Option("--debug", help="Enable debug logging"),
]


@app.command()
def scan(
    limit: LimitOpt = None,
    env_file: EnvFileOpt = None,
    rules_file: RulesFileOpt = None,
    debug: DebugOpt = False,
) -> None:
    """Preview email classification without moving anything."""
    _setup_logging(debug)
    try:
        sorter, imap = _build_sorter(env_file, rules_file)
        with imap:
            report = sorter.scan(limit=limit)
        _print_report(report, dry_run=True)
    except YahooMailSorterError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc


@app.command()
def sort(
    execute: Annotated[
        bool,
        typer.Option("--execute", help="Actually move emails (default is dry-run)"),
    ] = False,
    limit: LimitOpt = None,
    env_file: EnvFileOpt = None,
    rules_file: RulesFileOpt = None,
    debug: DebugOpt = False,
) -> None:
    """Classify and sort emails into folders."""
    _setup_logging(debug)
    try:
        sorter, imap = _build_sorter(env_file, rules_file)
        with imap:
            report = sorter.sort(execute=execute, limit=limit)
        _print_report(report, dry_run=not execute)
    except YahooMailSorterError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc


@app.command()
def clean(
    execute: Annotated[
        bool,
        typer.Option("--execute", help="Actually move spam (default is dry-run)"),
    ] = False,
    limit: LimitOpt = None,
    env_file: EnvFileOpt = None,
    rules_file: RulesFileOpt = None,
    debug: DebugOpt = False,
) -> None:
    """Move spam emails to Spam folder."""
    _setup_logging(debug)
    try:
        sorter, imap = _build_sorter(env_file, rules_file)
        with imap:
            report = sorter.clean(execute=execute, limit=limit)
        _print_report(report, dry_run=not execute)
    except YahooMailSorterError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc


@app.command()
def folders(
    env_file: EnvFileOpt = None,
    debug: DebugOpt = False,
) -> None:
    """List all IMAP folders."""
    _setup_logging(debug)
    try:
        config = load_config(env_path=env_file)
        imap = IMAPClient(config.imap)
        with imap:
            folder_list = imap.list_folders()
        console.print("[bold]IMAP Folders:[/bold]\n")
        for name in folder_list:
            console.print(f"  {name}")
    except YahooMailSorterError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    app()
