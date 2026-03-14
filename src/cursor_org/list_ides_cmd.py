"""Command to list supported IDEs and their configurations."""
import typer
from rich.console import Console
from rich.table import Table

from .parsers import list_supported_ides
from .constants import IDE_DEFAULT_PATHS


app = typer.Typer()
console = Console()


@app.command()
def list_ides():
    """
    List all supported IDE configurations and their transcript paths.
    """
    table = Table(title="Supported AI IDEs")
    table.add_column("IDE", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("Description", style="white")
    table.add_column("Default Paths", style="dim")

    supported_ides = list_supported_ides()
    
    for ide_name, description in supported_ides.items():
        paths = IDE_DEFAULT_PATHS.get(ide_name, [])
        
        if ide_name == "cursor":
            status = "[OK] Implemented"
        else:
            status = "[WIP] Planned"
        
        paths_str = "\n".join(paths[:2])
        if len(paths) > 2:
            paths_str += f"\n...and {len(paths) - 2} more"
        
        table.add_row(ide_name.title(), status, description, paths_str)
    
    console.print(table)
    console.print("\n[dim]To organize transcripts, use:[/dim]")
    console.print("  cursor-org organize [italic]<path-to-transcripts>[/italic] --ide cursor")
    console.print("  cursor-org organize [italic]<path>[/italic]  [dim]# Auto-detects IDE[/dim]")


if __name__ == "__main__":
    list_ides()
