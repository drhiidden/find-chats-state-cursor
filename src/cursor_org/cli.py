import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import importlib.metadata

from .parser import TranscriptParser

app = typer.Typer(
    name="cursor-org",
    help="Organize and rename Cursor chat transcripts.",
    add_completion=False,
)
console = Console()


@app.command()
def inspect(
    path: Path = typer.Argument(
        ..., help="Path to a .jsonl transcript file", exists=True
    ),
):
    """
    Inspect a transcript file and show extracted metadata.
    Does NOT modify any files.
    """
    try:
        parser = TranscriptParser(path)
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
    dry_run: bool = typer.Option(
        True, "--apply", help="Apply changes (default is dry-run)"
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

    Optionally generates summary.md files and syncs to .procontext structure.
    """
    from .parser import TranscriptParser
    from .renamer import rename_transcript_folder
    from .summary import generate_summary, save_summary
    from .integration import sync_to_procontext

    # Find all .jsonl files
    jsonl_files = list(target_dir.rglob("*.jsonl"))

    if not jsonl_files:
        console.print(f"[yellow]No .jsonl files found in {target_dir}[/yellow]")
        return

    console.print(f"Found {len(jsonl_files)} transcript(s)")

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No changes will be made[/yellow]")

    renamed_count = 0
    summaries_count = 0
    synced_count = 0

    for jsonl_file in jsonl_files:
        folder = jsonl_file.parent

        # Skip if already organized (not a UUID name)
        if len(folder.name) != 36 or folder.name.count("-") != 4:
            console.print(f"[dim]Skipping (already organized): {folder.name}[/dim]")
            continue

        try:
            # Parse metadata
            parser = TranscriptParser(jsonl_file)
            metadata = parser.parse()

            # Rename folder
            new_path = rename_transcript_folder(folder, metadata, dry_run=dry_run)

            if new_path:
                status = (
                    "[green]Would rename[/green]"
                    if dry_run
                    else "[green]Renamed[/green]"
                )
                console.print(f"{status}: {folder.name} -> {new_path.name}")
                renamed_count += 1

                # Generate summary if enabled
                if generate_summaries and not dry_run:
                    try:
                        messages = parser._read_messages()
                        summary_content = generate_summary(metadata, messages)
                        summary_path = new_path / "summary.md"
                        save_summary(summary_content, summary_path)
                        console.print("  [blue]Generated:[/blue] summary.md")
                        summaries_count += 1

                        # Sync to .procontext if enabled
                        if sync_procontext:
                            try:
                                procontext_path = sync_to_procontext(
                                    summary_content, metadata
                                )
                                console.print(
                                    f"  [magenta]Synced:[/magenta] {procontext_path.relative_to(Path.cwd())}"
                                )
                                synced_count += 1
                            except FileNotFoundError as e:
                                console.print(f"  [yellow]Warning:[/yellow] {e}")
                    except Exception as e:
                        console.print(
                            f"  [yellow]Warning:[/yellow] Failed to generate summary: {e}"
                        )

            else:
                console.print(f"[red]Failed to rename: {folder.name}[/red]")

        except Exception as e:
            console.print(f"[red]Error processing {folder.name}: {e}[/red]")

    console.print(
        f"\n[bold]Summary:[/bold] {renamed_count} folder(s) {'would be' if dry_run else 'were'} renamed"
    )

    if summaries_count > 0:
        console.print(f"[bold]Summaries:[/bold] {summaries_count} generated")

    if synced_count > 0:
        console.print(f"[bold]Synced:[/bold] {synced_count} to .procontext/sessions/")

    if dry_run and renamed_count > 0:
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
    except importlib.metadata.PackageNotFoundError:
        console.print("[yellow]cursor-org (development version)[/yellow]")


if __name__ == "__main__":
    app()
