"""Project navigation and shortcuts for easier access to transcripts."""
from pathlib import Path
from typing import List, Optional, Dict
from rich.console import Console
from rich.table import Table
import re

console = Console()


def get_cursor_projects_dir() -> Path:
    """Get the Cursor projects directory."""
    import os
    home = Path.home()
    
    # Windows
    cursor_dir = home / ".cursor" / "projects"
    if cursor_dir.exists():
        return cursor_dir
    
    # macOS/Linux alternative locations
    alt_paths = [
        home / "Library" / "Application Support" / "Cursor" / "User" / "projects",
        home / ".config" / "Cursor" / "User" / "projects",
    ]
    
    for path in alt_paths:
        if path.exists():
            return path
    
    return cursor_dir  # Return default even if doesn't exist


def parse_project_name(folder_name: str) -> tuple[str, str]:
    """Extract readable project name from Cursor's folder naming.
    
    Cursor uses format: c-Users-username-Documents-path-to-project
    This extracts the project name and a context hint.
    
    Returns:
        (project_name, context_hint) where context_hint helps differentiate duplicates
    """
    # Remove common prefixes
    name = folder_name
    
    # Pattern: c-Users-...-...-project-name or C-Users-...-project-name
    parts = name.split('-')
    
    # Skip common words
    skip_words = {'c', 'C', 'Users', 'druiz', 'Documents', 'Laboratorio', 
                  'AppData', 'Local', 'Temp', 'Projects', 'Code'}
    
    significant_parts = [p for p in parts if p and p not in skip_words]
    
    # For code-workspace, try to get parent folder for context
    if significant_parts and 'workspace' in significant_parts[-1].lower():
        # Get 2-3 parts before workspace for context
        context_parts = [p for p in significant_parts[:-1] if p][-2:]
        if context_parts:
            context = '/'.join(context_parts)
            project = significant_parts[-1] if significant_parts else folder_name
            return (project, context)
    
    # Use last 1-2 parts as project name
    if len(significant_parts) >= 2:
        project = '-'.join(significant_parts[-2:])
        # Context: parts before project
        context_parts = significant_parts[:-2]
        context = '/'.join(context_parts[-2:]) if len(context_parts) >= 2 else '/'.join(context_parts)
        return (project, context)
    elif significant_parts:
        return (significant_parts[-1], '')
    
    return (folder_name, '')


def list_cursor_projects() -> List[Dict]:
    """List all Cursor projects with their transcript info."""
    projects_dir = get_cursor_projects_dir()
    
    if not projects_dir.exists():
        return []
    
    projects = []
    
    for folder in projects_dir.iterdir():
        if not folder.is_dir():
            continue
        
        # Look for agent-transcripts folder
        transcripts_dir = folder / "agent-transcripts"
        
        if transcripts_dir.exists():
            # Count transcripts
            jsonl_files = list(transcripts_dir.rglob("*.jsonl"))
            transcript_count = len(jsonl_files)
            
            # Count organized folders
            organized = [
                d for d in transcripts_dir.iterdir() 
                if d.is_dir() and not d.name.startswith('.') and '-' in d.name
            ]
            organized_count = len([d for d in organized if len(d.name) > 36])
            
            project_name, context = parse_project_name(folder.name)
            
            projects.append({
                'name': project_name,
                'context': context,
                'full_name': folder.name,
                'path': folder,
                'transcripts_dir': transcripts_dir,
                'transcript_count': transcript_count,
                'organized_count': organized_count,
            })
    
    return sorted(projects, key=lambda x: (x['name'].lower(), x['context']))


def display_projects_table(projects: List[Dict]):
    """Display projects in a nice table."""
    if not projects:
        console.print("[yellow]No Cursor projects found with transcripts[/yellow]")
        return
    
    table = Table(title="Cursor Projects with Transcripts", show_lines=False)
    table.add_column("#", style="cyan", width=4)
    table.add_column("Project", style="green", width=20)
    table.add_column("Context", style="dim", width=25)
    table.add_column("Transcripts", style="yellow", justify="right", width=11)
    table.add_column("Organized", style="magenta", justify="right", width=10)
    
    for i, proj in enumerate(projects, 1):
        # Highlight projects with transcripts to organize
        name_style = "bold green" if proj['organized_count'] < proj['transcript_count'] else "green"
        
        table.add_row(
            str(i),
            f"[{name_style}]{proj['name']}[/{name_style}]",
            proj['context'] if proj['context'] else "[dim]—[/dim]",
            str(proj['transcript_count']),
            f"{proj['organized_count']}/{proj['transcript_count']}" if proj['transcript_count'] > 0 else "—",
        )
    
    console.print(table)
    
    # Summary
    total_transcripts = sum(p['transcript_count'] for p in projects)
    total_organized = sum(p['organized_count'] for p in projects)
    unorganized = total_transcripts - total_organized
    
    if total_transcripts > 0:
        console.print(f"\n[bold]Total:[/bold] {len(projects)} projects, {total_transcripts} transcripts")
        if unorganized > 0:
            console.print(f"[yellow]⚠ {unorganized} transcripts pending organization[/yellow]")


def get_project_by_index(index: int) -> Optional[Dict]:
    """Get project by its index in the list."""
    projects = list_cursor_projects()
    if 0 < index <= len(projects):
        return projects[index - 1]
    return None


def get_project_by_name(name: str) -> Optional[Dict]:
    """Get project by name or context (fuzzy match)."""
    projects = list_cursor_projects()
    name_lower = name.lower()
    
    # Exact match first
    for proj in projects:
        if proj['name'].lower() == name_lower:
            return proj
    
    # Partial match in name
    for proj in projects:
        if name_lower in proj['name'].lower():
            return proj
    
    # Match in context
    for proj in projects:
        if proj['context'] and name_lower in proj['context'].lower():
            return proj
    
    # Match in full name
    for proj in projects:
        if name_lower in proj['full_name'].lower():
            return proj
    
    return None


def create_shortcut(project_name: str, shortcut_name: Optional[str] = None) -> Path:
    """Create a PowerShell shortcut function for quick access.
    
    This creates a function in PowerShell profile that can be used like:
    PS> goto-find-chats
    """
    project = get_project_by_name(project_name)
    if not project:
        raise ValueError(f"Project not found: {project_name}")
    
    shortcut = shortcut_name or f"goto-{project['name']}"
    transcripts_path = project['transcripts_dir']
    
    # PowerShell profile path
    profile_path = Path.home() / "Documents" / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1"
    
    # Create function definition
    function_def = f'\nfunction {shortcut} {{ Set-Location "{transcripts_path}" }}\n'
    
    # Append to profile (create if doesn't exist)
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(profile_path, 'a', encoding='utf-8') as f:
        f.write(function_def)
    
    console.print(f"[green]Created shortcut:[/green] {shortcut}")
    console.print(f"[dim]Reload PowerShell or run: . $PROFILE[/dim]")
    
    return profile_path
