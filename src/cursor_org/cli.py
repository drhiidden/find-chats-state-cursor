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


@app.command()
def projects(
    filter_type: str = typer.Option(
        None, "--filter", help="Filter by type: workspace, json, or show all (default)"
    ),
    only_pending: bool = typer.Option(
        False, "--pending", help="Show only projects with unorganized transcripts"
    ),
    create_shortcut: str = typer.Option(
        None, "--shortcut", help="Create PowerShell shortcut for quick access (e.g., 'goto-myproject')"
    )
):
    """
    List all Cursor projects with transcripts and create navigation shortcuts.
    
    Use this to easily find and access projects without typing long paths.
    
    Examples:
        cursor-org projects                      # List all projects
        cursor-org projects --pending            # Only show projects needing organization
        cursor-org projects --filter workspace   # Only show code-workspace projects
        cursor-org projects --shortcut goto-fc   # Create shortcut for find-chats project
    """
    from .navigation import list_cursor_projects, display_projects_table, create_shortcut as make_shortcut
    
    projects_list = list_cursor_projects()
    
    if not projects_list:
        console.print("[yellow]No Cursor projects found with transcripts[/yellow]")
        return
    
    # Apply filters
    if filter_type:
        if filter_type.lower() == "workspace":
            projects_list = [p for p in projects_list if "workspace" in p['name'].lower()]
        elif filter_type.lower() == "json":
            projects_list = [p for p in projects_list if "json" in p['name'].lower()]
    
    if only_pending:
        projects_list = [p for p in projects_list if p['organized_count'] < p['transcript_count']]
    
    display_projects_table(projects_list)
    
    if create_shortcut:
        # Ask which project
        console.print(f"\n[bold]Enter project number or name to create shortcut '{create_shortcut}':[/bold]")
        
        # For now, try to find by partial match
        # In future, could make interactive
        console.print("[dim]Tip: Use project name from the table above[/dim]")


@app.command()
def goto(
    project: str = typer.Argument(
        ..., help="Project name or number from 'cursor-org projects' command"
    )
):
    """
    Print the path to a project's transcripts for easy navigation.
    
    Usage:
        cd $(cursor-org goto find-chats)        # Unix/Mac
        cd (cursor-org goto find-chats)         # PowerShell
        
    Or just copy the path:
        cursor-org goto find-chats
    """
    from .navigation import get_project_by_name, get_project_by_index
    
    # Try as index first
    try:
        index = int(project)
        proj = get_project_by_index(index)
    except ValueError:
        # Try as name
        proj = get_project_by_name(project)
    
    if not proj:
        console.print(f"[red]Project not found:[/red] {project}")
        console.print("[dim]Run 'cursor-org projects' to see available projects[/dim]")
        raise typer.Exit(code=1)
    
    # Print the path (can be used with cd)
    console.print(str(proj['transcripts_dir']))


@app.command()
def clean(
    target_dir: Path = typer.Argument(
        ..., help="Directory to clean up", exists=True
    ),
    apply: bool = typer.Option(
        False, "--apply", help="Actually delete folders (default is dry-run)"
    ),
    max_depth: int = typer.Option(
        3, "--max-depth", help="Maximum depth to scan for cleanup"
    ),
    all_projects: bool = typer.Option(
        False, "--all", help="Clean all Cursor projects"
    ),
):
    """
    Clean up empty and irrelevant folders (MCP, agent-tools, etc.).
    
    Identifies and removes:
    - Empty folders (no files)
    - MCP folders without transcripts
    - agent-tools folders without content
    - Folders with only hidden/system files
    
    Examples:
        cursor-org clean /path/to/transcripts              # Dry-run (preview)
        cursor-org clean /path/to/transcripts --apply      # Actually delete
        cursor-org clean /path/to/transcripts --all        # Clean all projects
    """
    from .cleanup import TranscriptCleaner, clean_all_projects
    
    if all_projects:
        # Clean all projects
        console.print("[bold]Cleaning all Cursor projects...[/bold]\n")
        
        all_results = clean_all_projects(dry_run=not apply, max_depth=max_depth)
        
        if not all_results:
            console.print("[green]No folders to clean up in any project![/green]")
            return
        
        # Display results per project
        for proj_name, results in all_results.items():
            console.print(f"\n[bold cyan]Project: {proj_name}[/bold cyan]")
            
            from rich.table import Table
            table = Table(show_header=True)
            table.add_column("Path", style="yellow")
            table.add_column("Reason", style="dim")
            table.add_column("Size", style="cyan", justify="right")
            
            for result in results:
                table.add_row(
                    result.path.name,
                    result.reason,
                    f"{result.size_kb:.1f} KB"
                )
            
            console.print(table)
        
        # Overall summary
        total_folders = sum(len(r) for r in all_results.values())
        total_size = sum(r.size_kb for results in all_results.values() for r in results)
        
        console.print(f"\n[bold]Overall:[/bold]")
        console.print(f"  Projects affected: {len(all_results)}")
        console.print(f"  Total folders: {total_folders}")
        console.print(f"  Total size: {total_size:.1f} KB ({total_size/1024:.2f} MB)")
        
        if not apply:
            console.print(f"\n[yellow]DRY RUN - Run with --apply to delete[/yellow]")
    
    else:
        # Clean single directory
        cleaner = TranscriptCleaner(target_dir, dry_run=not apply)
        cleaner.clean(max_depth=max_depth)
        cleaner.display_results()


if __name__ == "__main__":
    app()
