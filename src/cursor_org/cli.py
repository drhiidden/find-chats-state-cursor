import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import importlib.metadata

from .parser import TranscriptParser
from .parsers import auto_detect_ide
from .constants import (
    DEFAULT_IDE, CLI_MSG_AUTO_DETECTED, CLI_MSG_DEFAULT_IDE,
    CLI_MSG_DRY_RUN, CLI_MSG_SKIPPING_ORGANIZED,
    CLI_MSG_RENAMED, CLI_MSG_WOULD_RENAME, CLI_MSG_GENERATED_SUMMARY,
    UUID_LENGTH, UUID_DASH_COUNT,
)

app = typer.Typer(
    name="cursor-org",
    help="Organize and analyze AI coding assistant transcripts (Cursor, Claude Code, Continue.dev, etc.)",
    add_completion=False,
)
console = Console()


@app.command()
def inspect(
    path: Path = typer.Argument(
        ..., help="Path to a .jsonl transcript file", exists=True
    ),
    ide: str = typer.Option(
        None, "--ide", help="IDE type (cursor, claude, continue). Auto-detected if not specified."
    ),
):
    """
    Inspect a transcript file and show extracted metadata.
    Does NOT modify any files.
    """
    try:
        # Auto-detect IDE if not specified
        if ide is None:
            ide = auto_detect_ide(path)
            if ide:
                console.print(f"[dim]{CLI_MSG_AUTO_DETECTED.format(ide)}[/dim]")
            else:
                ide = DEFAULT_IDE
                console.print(f"[dim]{CLI_MSG_DEFAULT_IDE.format(ide)}[/dim]")
        
        parser = TranscriptParser(path, ide=ide)
        metadata = parser.parse()

        # Display Core Info
        table = Table(title=f"Transcript Analysis: {metadata.uuid_short}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("UUID", metadata.uuid)
        table.add_row("Topic (Raw)", metadata.topic_raw)
        table.add_row("Topic (Slug)", metadata.topic_slug)
        table.add_row("Start Time", metadata.start_time.strftime("%Y-%m-%d %H:%M:%S"))
        table.add_row("End Time", metadata.end_time.strftime("%Y-%m-%d %H:%M:%S"))
        table.add_row(
            "Messages",
            f"{metadata.message_count} (User: {metadata.user_messages}, Assistant: {metadata.assistant_messages})",
        )
        table.add_row("Suggested Name", metadata.suggested_dirname)

        console.print(table)

        # Display Injected Metadata if present
        if metadata.injected_role or metadata.injected_goal or metadata.injected_files:
            injected_table = Table(title="Injected Metadata (Prompt Engineering)")
            injected_table.add_column("Key", style="magenta")
            injected_table.add_column("Value", style="yellow")

            if metadata.injected_role:
                injected_table.add_row("Role", metadata.injected_role)
            if metadata.injected_goal:
                injected_table.add_row("Goal", metadata.injected_goal)
            if metadata.injected_status:
                injected_table.add_row("Status", metadata.injected_status)
            if metadata.injected_files:
                injected_table.add_row(
                    "Files Modified", "\n".join(metadata.injected_files)
                )

            console.print(injected_table)
        else:
            console.print(
                Panel(
                    "No injected metadata found. Use <session_metadata> blocks to enhance accuracy.",
                    title="Info",
                    style="dim",
                )
            )

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def organize(
    target_dir: Path = typer.Argument(
        ..., help="Directory containing transcripts", exists=True
    ),
    apply: bool = typer.Option(
        False, "--apply", help="Apply changes (default is dry-run)"
    ),
    ide: str = typer.Option(
        None, "--ide", help="IDE type (cursor, claude, continue). Auto-detected if not specified."
    ),
    recursive: bool = typer.Option(
        True, "--no-recursive", help="Process nested transcripts (e.g., subagents)"
    ),
    generate_summaries: bool = typer.Option(
        True, "--no-summaries", help="Generate summary.md for each transcript"
    ),
    sync_procontext: bool = typer.Option(
        False, "--sync-procontext", help="Sync summaries to .procontext/sessions/"
    ),
):
    """
    Rename transcript folders to human-readable format and generate summaries.

    Scans for UUID folders containing .jsonl files and renames them to:
    YYYY-MM-DD_HHhMM_topic-slug_uuid

    With --recursive, also organizes nested transcripts (e.g., subagents).
    """
    from .organizer import organize_recursively
    from .parser import TranscriptParser
    from .summary import generate_summary, save_summary
    from .integration import sync_to_procontext

    # Auto-detect IDE if not specified
    if ide is None:
        ide = auto_detect_ide(target_dir)
        if ide:
            console.print(f"[dim]{CLI_MSG_AUTO_DETECTED.format(ide)}[/dim]")
        else:
            ide = DEFAULT_IDE
            console.print(f"[dim]{CLI_MSG_DEFAULT_IDE.format(ide)}[/dim]")

    dry_run = not apply
    if dry_run:
        console.print(f"[yellow]{CLI_MSG_DRY_RUN}[/yellow]")

    # Use new recursive organizer
    results = organize_recursively(
        root_dir=target_dir,
        dry_run=dry_run,
        ide=ide,
        organize_nested=recursive
    )

    # Display main transcript results
    main_results = results['main']
    for result in main_results:
        if result.skipped:
            console.print(f"[dim]Skipping: {result.skip_reason}[/dim]")
        elif result.success:
            status = (
                f"[green]{CLI_MSG_WOULD_RENAME}[/green]"
                if dry_run
                else f"[green]{CLI_MSG_RENAMED}[/green]"
            )
            original_name = result.original_path.parent.name
            new_name = result.new_path.name if result.new_path else "N/A"
            console.print(f"{status}: {original_name} -> {new_name}")
            
            # Generate summary if enabled
            if generate_summaries and not dry_run and result.metadata:
                try:
                    parser = TranscriptParser(result.original_path, ide=ide)
                    messages = parser._parser._read_messages()
                    summary_content = generate_summary(result.metadata, messages)
                    summary_path = result.new_path / "summary.md"
                    save_summary(summary_content, summary_path)
                    console.print(f"  [blue]{CLI_MSG_GENERATED_SUMMARY}[/blue]")

                    # Sync to .procontext if enabled
                    if sync_procontext:
                        try:
                            procontext_path = sync_to_procontext(
                                summary_content, result.metadata
                            )
                            console.print(
                                f"  [magenta]Synced:[/magenta] {procontext_path.relative_to(Path.cwd())}"
                            )
                        except FileNotFoundError as e:
                            console.print(f"  [yellow]Warning:[/yellow] {e}")
                except Exception as e:
                    console.print(
                        f"  [yellow]Warning:[/yellow] Failed to generate summary: {e}"
                    )
        else:
            console.print(f"[red]Error: {result.error}[/red]")

    # Display nested transcript results
    if recursive and results['nested']:
        console.print(f"\n[bold]Nested Transcripts:[/bold]")
        for result in results['nested']:
            if result.skipped:
                console.print(f"[dim]  Skipping: {result.skip_reason}[/dim]")
            elif result.success:
                status = "[green]Renamed[/green]" if not dry_run else "[green]Would rename[/green]"
                rel_path = result.original_path.relative_to(target_dir)
                new_name = result.new_path.name if result.new_path else "N/A"
                console.print(f"{status}: {rel_path} -> {new_name}")
            else:
                console.print(f"[red]  Error: {result.error}[/red]")

    # Summary
    summary = results['summary']
    console.print(
        f"\n[bold]Summary:[/bold] "
        f"{summary['organized_main']}/{summary['total_main']} main transcript(s) "
        f"{'would be' if dry_run else 'were'} renamed"
    )

    if recursive and summary['total_nested'] > 0:
        console.print(
            f"[bold]Nested:[/bold] "
            f"{summary['organized_nested']}/{summary['total_nested']} nested transcript(s) "
            f"{'would be' if dry_run else 'were'} renamed"
        )

    if dry_run and (summary['organized_main'] > 0 or summary['organized_nested'] > 0):
        console.print("[yellow]Run with --apply to execute changes[/yellow]")


@app.command()
def stats(
    directory: Path = typer.Argument(
        ..., help="Directory containing transcripts", exists=True
    )
):
    """
    Show statistics about transcripts in a directory.

    Displays total sessions, messages, duration, token usage, top topics,
    and activity by day.
    """
    from .stats import calculate_statistics, display_statistics

    try:
        stats = calculate_statistics(directory)
        display_statistics(stats)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def version():
    """Show version information."""
    try:
        ver = importlib.metadata.version("cursor-transcript-organizer")
        console.print(f"[bold green]cursor-org[/bold green] version [cyan]{ver}[/cyan]")
        console.print("[dim]IDE-agnostic transcript organizer for AI coding assistants[/dim]")
    except importlib.metadata.PackageNotFoundError:
        console.print("[yellow]cursor-org (development version)[/yellow]")


@app.command()
def list_ides():
    """
    List all supported IDE configurations and their transcript paths.
    """
    from .list_ides_cmd import list_ides as _list_ides
    _list_ides()


if __name__ == "__main__":
    app()
