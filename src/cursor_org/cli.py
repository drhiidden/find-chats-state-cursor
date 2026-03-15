import typer
import json
from pathlib import Path
from typing import Optional
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
from .validation import (
    validate_organize_command,
    validate_clean_command,
    validate_inspect_command,
)
from .errors import (
    TranscriptOrgError,
    PathNotFoundError,
    NotADirectoryError,
    PermissionError as CursorPermissionError,
    NoTranscriptsFoundError,
    format_error_message,
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
        ..., help="Path to a .jsonl transcript file"
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
        # Validate input
        is_valid, validation_result = validate_inspect_command(path)
        if not is_valid:
            if validation_result.error_type in ["PATH_NOT_FOUND", "NOT_A_FILE", "INVALID_FILE_TYPE"]:
                console.print(format_error_message(
                    validation_result.error_type,
                    path=validation_result.details.get("path", str(path)),
                    name=validation_result.details.get("name", path.name),
                    suffix=validation_result.details.get("suffix", "")
                ))
            else:
                console.print(f"[bold red]Error:[/bold red] {validation_result.message}")
                if validation_result.suggestions:
                    console.print("\n[yellow]Suggestions:[/yellow]")
                    for suggestion in validation_result.suggestions:
                        console.print(f"  • {suggestion}")
            raise typer.Exit(code=1)
        
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

    except TranscriptOrgError as e:
        console.print(e.format_message())
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        console.print("\n[dim]Run with --help for usage information[/dim]")
        raise typer.Exit(code=1)


@app.command()
def organize(
    target_dir: Path = typer.Argument(
        ..., help="Directory containing transcripts"
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
    no_backup: bool = typer.Option(
        False, "--no-backup", help="Skip backup creation (advanced users only)"
    ),
):
    """
    Rename transcript folders to human-readable format and generate summaries.

    Scans for UUID folders containing .jsonl files and renames them to:
    YYYY-MM-DD_HHhMM_topic-slug_uuid

    With --recursive, also organizes nested transcripts (e.g., subagents).
    
    SAFETY: Automatic backup is created before renaming (use --no-backup to skip).
    """
    from .organizer import organize_recursively
    from .parser import TranscriptParser
    from .summary import generate_summary, save_summary
    from .integration import sync_to_procontext
    from .backup import BackupManager
    from .collector import TranscriptCollector, FileFilter

    try:
        # Validate input with comprehensive checks
        is_valid, validation_result = validate_organize_command(target_dir, apply=apply)
        
        if not is_valid:
            # Handle warnings (non-fatal)
            if validation_result.is_warning:
                if validation_result.error_type == "NO_TRANSCRIPTS":
                    console.print(format_error_message(
                        "NO_TRANSCRIPTS",
                        path=validation_result.details.get("path", str(target_dir))
                    ))
                elif validation_result.error_type == "NO_FOLDERS_TO_ORGANIZE":
                    console.print(format_error_message(
                        "NO_FOLDERS_TO_ORGANIZE",
                        path=validation_result.details.get("path", str(target_dir))
                    ))
                raise typer.Exit(code=0)  # Exit gracefully for warnings
            
            # Handle fatal errors
            console.print(f"[bold red]Error:[/bold red] {validation_result.message}")
            if validation_result.suggestions:
                console.print("\n[yellow]Suggestions:[/yellow]")
                for suggestion in validation_result.suggestions:
                    console.print(f"  • {suggestion}")
            console.print("\n[dim]Need help? Run: cursor-org --help[/dim]")
            raise typer.Exit(code=1)

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
        
        # Create backup before organizing (if --apply and not --no-backup)
        backup_id = None
        if not dry_run and not no_backup:
            collector = TranscriptCollector(target_dir)
            folders_to_backup = []
            
            for transcript in collector.collect_all(max_depth=1):
                if FileFilter.is_uuid_folder(transcript.parent_dir):
                    folders_to_backup.append(transcript.parent_dir)
            
            if folders_to_backup:
                backup_manager = BackupManager(target_dir)
                backup_id = backup_manager.create_backup(
                    items_to_backup=folders_to_backup,
                    operation_type='organize'
                )
                
                if backup_id is None:
                    console.print("[red]Error:[/red] Backup failed, aborting operation")
                    raise typer.Exit(code=1)

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

    except TranscriptOrgError as e:
        console.print(e.format_message())
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        console.print("\n[dim]This may be a bug. Please report it with the error details.[/dim]")
        console.print(f"[dim]Run with --help for usage information[/dim]")
        raise typer.Exit(code=1)


@app.command()
def stats(
    directory: Path = typer.Argument(
        ..., help="Directory containing transcripts"
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
        ..., help="Directory to clean up"
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
    no_backup: bool = typer.Option(
        False, "--no-backup", help="Skip backup creation (advanced users only)"
    ),
):
    """
    Clean up empty and irrelevant folders (MCP, agent-tools, etc.).
    
    Identifies and removes:
    - Empty folders (no files)
    - MCP folders without transcripts
    - agent-tools folders without content
    - Folders with only hidden/system files
    
    SAFETY: Automatic backup is created before deletion (use --no-backup to skip).
    
    Examples:
        cursor-org clean /path/to/transcripts              # Dry-run (preview)
        cursor-org clean /path/to/transcripts --apply      # Actually delete
        cursor-org clean /path/to/transcripts --all        # Clean all projects
    """
    from .cleanup import TranscriptCleaner, clean_all_projects
    from .backup import BackupManager
    
    try:
        if all_projects:
            # Clean all projects
            console.print("[bold]Cleaning all Cursor projects...[/bold]\n")
            
            # Note about backups in --all mode
            if apply and not no_backup:
                console.print("[yellow]Note:[/yellow] Backups will be created per-project\n")
            
            all_results = clean_all_projects(
                dry_run=not apply, 
                max_depth=max_depth,
                create_backup=(apply and not no_backup)
            )
            
            if not all_results:
                console.print("[green]✓ Success: No folders to clean up in any project![/green]")
                console.print("\n[dim]All projects are already clean 🎉[/dim]")
                return
            
            # Display results per project
            for proj_name, results in all_results.items():
                console.print(f"\n[bold cyan]Project: {proj_name}[/bold cyan]")
                
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
            # Validate single directory cleanup
            is_valid, validation_result = validate_clean_command(target_dir, apply=apply, max_depth=max_depth)
            
            if not is_valid:
                # Handle warnings (non-fatal)
                if validation_result.is_warning:
                    if validation_result.error_type == "NO_FOLDERS_TO_CLEAN":
                        console.print(format_error_message(
                            "NO_FOLDERS_TO_CLEAN",
                            path=validation_result.details.get("path", str(target_dir))
                        ))
                    raise typer.Exit(code=0)  # Exit gracefully for warnings
                
                # Handle errors (fatal)
                console.print(f"[bold red]Error:[/bold red] {validation_result.message}")
                if validation_result.suggestions:
                    console.print("\n[yellow]Suggestions:[/yellow]")
                    for suggestion in validation_result.suggestions:
                        console.print(f"  • {suggestion}")
                console.print("\n[dim]Need help? Run: cursor-org clean --help[/dim]")
                raise typer.Exit(code=1)
            
            # Clean single directory
            # Create backup before cleaning (if --apply and not --no-backup)
            backup_id = None
            if apply and not no_backup:
                cleaner_scan = TranscriptCleaner(target_dir, dry_run=True)
                folders_to_cleanup = cleaner_scan.scan_for_cleanup(max_depth=max_depth)
                
                if folders_to_cleanup:
                    backup_manager = BackupManager(target_dir)
                    backup_id = backup_manager.create_backup(
                        items_to_backup=[r.path for r in folders_to_cleanup],
                        operation_type='clean'
                    )
                    
                    if backup_id is None:
                        console.print("[red]Error:[/red] Backup failed, aborting operation")
                        raise typer.Exit(code=1)
            
            cleaner = TranscriptCleaner(target_dir, dry_run=not apply)
            cleaner.clean(max_depth=max_depth)
            cleaner.display_results()

    except TranscriptOrgError as e:
        console.print(e.format_message())
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        console.print("\n[dim]This may be a bug. Please report it with the error details.[/dim]")
        console.print(f"[dim]Run with --help for usage information[/dim]")
        raise typer.Exit(code=1)


@app.command()
def search(
    query: str = typer.Argument(
        ..., help="Text to search for in transcripts"
    ),
    path: Path = typer.Argument(
        None, help="Directory to search (defaults to current directory)"
    ),
    date_from: str = typer.Option(
        None, "--date-from", help="Filter by start date (YYYY-MM-DD)"
    ),
    date_to: str = typer.Option(
        None, "--date-to", help="Filter by end date (YYYY-MM-DD)"
    ),
    tags: str = typer.Option(
        None, "--tags", help="Filter by tags (comma-separated)"
    ),
    case_sensitive: bool = typer.Option(
        False, "--case-sensitive", help="Enable case-sensitive search"
    ),
    organized_only: bool = typer.Option(
        False, "--organized-only", help="Only search organized transcripts"
    ),
    limit: int = typer.Option(
        None, "--limit", help="Limit number of results"
    ),
    context: int = typer.Option(
        0, "--context", help="Number of context lines before/after match"
    ),
    ide: str = typer.Option(
        None, "--ide", help="IDE type (cursor, claude, continue). Auto-detected if not specified."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show snippets for each match"
    ),
):
    """
    Search for text in transcripts and summaries.
    
    Examples:
        cursor-org search "authentication"                  # Simple search
        cursor-org search "JWT" /path/to/transcripts        # Search in specific path
        cursor-org search "bug" --date-from 2026-03-01      # Filter by date
        cursor-org search "auth" --tags security,api        # Filter by tags
        cursor-org search "error" --case-sensitive -v       # Case-sensitive with snippets
    """
    from .search import TranscriptSearcher, SearchOptions
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from datetime import datetime
    
    # Use current directory if path not specified
    if path is None:
        path = Path.cwd()
    
    if not path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {path}")
        raise typer.Exit(code=1)
    
    # Parse dates
    date_from_obj = None
    date_to_obj = None
    
    try:
        if date_from:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
        if date_to:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
    except ValueError as e:
        console.print(f"[red]Error:[/red] Invalid date format. Use YYYY-MM-DD: {e}")
        raise typer.Exit(code=1)
    
    # Parse tags
    tags_list = []
    if tags:
        tags_list = [t.strip() for t in tags.split(',')]
    
    # Create searcher
    searcher = TranscriptSearcher(path, ide=ide)
    
    # Search with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description="Searching transcripts...", total=None)
        
        options = SearchOptions(
            case_sensitive=case_sensitive,
            date_from=date_from_obj,
            date_to=date_to_obj,
            tags=tags_list,
            organized_only=organized_only,
            context_lines=context,
            limit=limit
        )
        
        results = searcher.search_text(query, options)
    
    # Display results
    if not results:
        console.print("[yellow]No matches found.[/yellow]")
        return
    
    # Summary
    total_matches = sum(r.match_count for r in results)
    console.print(
        f"\n[bold green]Found {total_matches} matches in {len(results)} transcript(s)[/bold green]\n"
    )
    
    # Create results table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Date", style="green", width=12)
    table.add_column("Topic", style="cyan", no_wrap=False)
    table.add_column("Matches", justify="right", style="yellow", width=8)
    table.add_column("Path", style="dim", no_wrap=False)
    
    for result in results:
        # Truncate topic if too long
        topic = result.topic
        if len(topic) > 50:
            topic = topic[:47] + "..."
        
        # Get relative path
        try:
            rel_path = result.transcript_path.relative_to(path)
        except ValueError:
            rel_path = result.transcript_path
        
        table.add_row(
            result.date_str,
            topic,
            str(result.match_count),
            str(rel_path.parent.name) if rel_path.parent.name else str(rel_path)
        )
    
    console.print(table)
    
    # Show snippets if verbose
    if verbose and results:
        console.print("\n[bold]Snippets:[/bold]\n")
        for result in results[:10]:  # Limit to first 10 for readability
            if result.snippets:
                console.print(f"[cyan]{result.topic}[/cyan] ({result.date_str})")
                for snippet in result.snippets[:3]:  # Max 3 snippets per result
                    # Highlight query in snippet
                    highlighted = snippet
                    if not case_sensitive:
                        # Case-insensitive highlighting
                        import re
                        pattern = re.compile(re.escape(query), re.IGNORECASE)
                        highlighted = pattern.sub(
                            lambda m: f"[bold yellow]{m.group()}[/bold yellow]",
                            snippet
                        )
                    else:
                        highlighted = snippet.replace(
                            query,
                            f"[bold yellow]{query}[/bold yellow]"
                        )
                    console.print(f"  {highlighted}")
                console.print()


@app.command()
def undo(
    backup_id: Optional[str] = typer.Argument(
        None, help="Backup ID or index to restore (leave empty to list backups)"
    ),
    work_dir: Optional[Path] = typer.Option(
        None, "--work-dir", help="Working directory where backups are stored (default: current directory)"
    ),
):
    """
    Restore a previous backup to undo changes.
    
    List available backups:
        cursor-org undo
    
    Restore a specific backup:
        cursor-org undo 1                    # By index
        cursor-org undo 2026-03-14_15h30h45_organize  # By ID
    
    This command allows you to undo changes made by 'organize' and 'clean' operations.
    """
    from .backup import BackupManager, display_backups_table
    
    # Determine work directory
    if work_dir is None:
        work_dir = Path.cwd()
    
    backup_manager = BackupManager(work_dir)
    
    # If no backup_id provided, list backups
    if backup_id is None:
        backups = backup_manager.list_backups()
        display_backups_table(backups)
        return
    
    # Restore specified backup
    result = backup_manager.restore_backup(backup_id, confirm=False)
    
    if not result.success:
        raise typer.Exit(code=1)


@app.command()
def backups(
    work_dir: Optional[Path] = typer.Option(
        None, "--work-dir", help="Working directory where backups are stored (default: current directory)"
    ),
    delete: Optional[str] = typer.Option(
        None, "--delete", help="Delete a specific backup by ID or index"
    ),
    cleanup: bool = typer.Option(
        False, "--cleanup", help="Manually trigger cleanup of old backups"
    ),
):
    """
    Manage backups created by cursor-org.
    
    List backups:
        cursor-org backups
    
    Delete a specific backup:
        cursor-org backups --delete 1
        cursor-org backups --delete 2026-03-14_15h30h45_organize
    
    Cleanup old backups:
        cursor-org backups --cleanup
    """
    from .backup import BackupManager, display_backups_table
    
    # Determine work directory
    if work_dir is None:
        work_dir = Path.cwd()
    
    backup_manager = BackupManager(work_dir)
    
    # Delete backup
    if delete:
        backup_manager.delete_backup(delete)
        return
    
    # Cleanup old backups
    if cleanup:
        removed = backup_manager.cleanup_old_backups()
        if removed == 0:
            console.print("[green]No old backups to cleanup[/green]")
        return
    
    # List backups
    backups = backup_manager.list_backups()
    display_backups_table(backups)


@app.command()
def export(
    transcript_path: Path = typer.Argument(
        ..., help="Path to transcript file or folder to export"
    ),
    format: str = typer.Option(
        "json", "--format", "-f", help="Export format: json, markdown, html, cjson"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file path (default: auto-generated)"
    ),
    ide: str = typer.Option(
        None, "--ide", help="IDE type (cursor, claude, continue). Auto-detected if not specified."
    ),
):
    """
    Export transcript to various formats.
    
    Formats:
        json     - Structured JSON with full metadata (AITS v1.0 compliant)
        markdown - Enhanced markdown with conversation and metadata
        html     - Styled HTML report
        cjson    - Common JSON format for interoperability
    
    Examples:
        cursor-org export path/to/transcript.jsonl --format json
        cursor-org export path/to/transcript.jsonl --format markdown -o report.md
        cursor-org export ~/.claude/projects/myapp/sessions/abc123.jsonl --format html
    """
    from .exporters import (
        export_to_json, export_to_markdown, export_to_html, export_to_cjson
    )
    from .parser import TranscriptParser
    
    try:
        # Validate transcript path
        if not transcript_path.exists():
            console.print(f"[red]Error: Path not found: {transcript_path}[/red]")
            raise typer.Exit(code=1)
        
        # If path is directory, look for .jsonl file
        if transcript_path.is_dir():
            jsonl_files = list(transcript_path.glob("*.jsonl"))
            if not jsonl_files:
                console.print(f"[red]Error: No .jsonl files found in {transcript_path}[/red]")
                raise typer.Exit(code=1)
            transcript_path = jsonl_files[0]
            console.print(f"[dim]Using file: {transcript_path.name}[/dim]")
        
        # Auto-detect IDE if not specified
        if ide is None:
            ide = auto_detect_ide(transcript_path)
            if ide:
                console.print(f"[dim]{CLI_MSG_AUTO_DETECTED.format(ide)}[/dim]")
            else:
                ide = DEFAULT_IDE
                console.print(f"[dim]{CLI_MSG_DEFAULT_IDE.format(ide)}[/dim]")
        
        # Parse transcript
        console.print(f"[cyan]Parsing transcript...[/cyan]")
        parser = TranscriptParser(transcript_path, ide=ide)
        metadata = parser.parse()
        
        # Read messages (need raw messages for full export)
        with open(transcript_path, "r", encoding="utf-8") as f:
            messages = []
            for line in f:
                line = line.strip()
                if line:
                    try:
                        messages.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        
        # Generate output filename if not specified
        if output is None:
            base_name = transcript_path.stem
            extension_map = {
                "json": "json",
                "markdown": "md",
                "html": "html",
                "cjson": "cjson.json"
            }
            ext = extension_map.get(format, "txt")
            output = transcript_path.parent / f"{base_name}_export.{ext}"
        
        # Export based on format
        format_lower = format.lower()
        
        if format_lower == "json":
            export_to_json(metadata, messages, output)
            console.print(f"[green]✓ Exported to JSON: {output}[/green]")
        
        elif format_lower == "markdown":
            export_to_markdown(metadata, messages, output)
            console.print(f"[green]✓ Exported to Markdown: {output}[/green]")
        
        elif format_lower == "html":
            export_to_html(metadata, messages, output)
            console.print(f"[green]✓ Exported to HTML: {output}[/green]")
        
        elif format_lower == "cjson":
            export_to_cjson(metadata, messages, output)
            console.print(f"[green]✓ Exported to CJSON: {output}[/green]")
        
        else:
            console.print(f"[red]Error: Unsupported format '{format}'[/red]")
            console.print("[yellow]Supported formats: json, markdown, html, cjson[/yellow]")
            raise typer.Exit(code=1)
        
        # Show summary
        console.print(f"\n[cyan]Export Summary:[/cyan]")
        console.print(f"  Format: {format}")
        console.print(f"  UUID: {metadata.uuid}")
        console.print(f"  Title: {metadata.title}")
        console.print(f"  Messages: {metadata.message_count}")
        console.print(f"  Output: {output}")
        
    except Exception as e:
        console.print(f"[red]Export failed: {str(e)}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
