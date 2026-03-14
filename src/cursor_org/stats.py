"""Generate statistics about transcript collections."""

from pathlib import Path
from typing import Dict, List, Any
from collections import Counter

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .parser import TranscriptParser

console = Console()


def calculate_statistics(transcripts_dir: Path) -> Dict[str, Any]:
    """
    Calculate comprehensive statistics from a directory of transcripts.

    Args:
        transcripts_dir: Directory containing transcript folders with .jsonl files

    Returns:
        Dictionary with statistics
    """
    # Find all .jsonl files
    jsonl_files = list(transcripts_dir.rglob("*.jsonl"))

    if not jsonl_files:
        return {
            "total_sessions": 0,
            "total_messages": 0,
            "user_messages": 0,
            "assistant_messages": 0,
            "total_duration_seconds": 0,
            "token_usage": {"input": 0, "output": 0, "total": 0},
            "topics": [],
            "activity_by_day": {},
        }

    total_messages = 0
    user_messages = 0
    assistant_messages = 0
    total_duration_seconds = 0
    total_input_tokens = 0
    total_output_tokens = 0
    topics = []
    activity_by_day = Counter()

    for jsonl_file in jsonl_files:
        try:
            # Parse metadata
            parser = TranscriptParser(jsonl_file)
            metadata = parser.parse()

            # Aggregate stats
            total_messages += metadata.message_count
            user_messages += metadata.user_messages
            assistant_messages += metadata.assistant_messages

            # Duration
            duration = metadata.end_time - metadata.start_time
            total_duration_seconds += duration.total_seconds()

            # Topic
            topics.append(metadata.topic_raw)

            # Activity by day
            day_str = metadata.start_time.strftime("%Y-%m-%d")
            activity_by_day[day_str] += 1

            # Token usage
            messages = parser._read_messages()
            tokens = _extract_token_usage(messages)
            total_input_tokens += tokens["input"]
            total_output_tokens += tokens["output"]

        except Exception as e:
            console.print(f"[yellow]Warning: Failed to parse {jsonl_file.name}: {e}[/yellow]")
            continue

    return {
        "total_sessions": len(jsonl_files),
        "total_messages": total_messages,
        "user_messages": user_messages,
        "assistant_messages": assistant_messages,
        "total_duration_seconds": total_duration_seconds,
        "token_usage": {
            "input": total_input_tokens,
            "output": total_output_tokens,
            "total": total_input_tokens + total_output_tokens,
        },
        "topics": topics,
        "activity_by_day": dict(activity_by_day),
    }


def _extract_token_usage(messages: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Extract token usage from messages if available.

    Args:
        messages: List of message dictionaries from .jsonl file

    Returns:
        Dictionary with input, output, and total token counts
    """
    total_input = 0
    total_output = 0

    for msg in messages:
        # Check for tokenUsage field in message
        token_usage = msg.get("tokenUsage")
        if token_usage:
            total_input += token_usage.get("input", 0)
            total_output += token_usage.get("output", 0)

    return {"input": total_input, "output": total_output, "total": total_input + total_output}


def get_top_topics(topics: List[str], n: int = 5) -> List[tuple]:
    """
    Get the top N most frequent topics.

    Args:
        topics: List of topic strings
        n: Number of top topics to return

    Returns:
        List of (topic, count) tuples
    """
    # Truncate topics to 60 chars for comparison
    normalized_topics = [t[:60] for t in topics]
    counter = Counter(normalized_topics)
    return counter.most_common(n)


def display_statistics(stats: Dict[str, Any]) -> None:
    """
    Display statistics in a formatted way using Rich.

    Args:
        stats: Statistics dictionary from calculate_statistics()
    """
    if stats["total_sessions"] == 0:
        console.print("[yellow]No transcripts found.[/yellow]")
        return

    # Overview Table
    overview_table = Table(title="Transcript Statistics Overview")
    overview_table.add_column("Metric", style="cyan", no_wrap=True)
    overview_table.add_column("Value", style="green")

    overview_table.add_row("Total Sessions", str(stats["total_sessions"]))
    overview_table.add_row(
        "Total Messages",
        f"{stats['total_messages']:,} ({stats['user_messages']:,} user, {stats['assistant_messages']:,} assistant)",
    )

    # Duration
    duration_str = _format_duration(stats["total_duration_seconds"])
    avg_duration_str = _format_duration(stats["total_duration_seconds"] / stats["total_sessions"])
    overview_table.add_row("Total Duration", duration_str)
    overview_table.add_row("Avg Duration/Session", avg_duration_str)

    # Tokens
    if stats["token_usage"]["total"] > 0:
        overview_table.add_row(
            "Total Tokens",
            f"{stats['token_usage']['total']:,} ({stats['token_usage']['input']:,} input, {stats['token_usage']['output']:,} output)",
        )

    console.print(overview_table)
    console.print()

    # Top Topics
    if stats["topics"]:
        top_topics = get_top_topics(stats["topics"], n=5)
        topics_table = Table(title="Top 5 Most Frequent Topics")
        topics_table.add_column("Topic", style="magenta")
        topics_table.add_column("Count", style="yellow", justify="right")

        for topic, count in top_topics:
            topics_table.add_row(topic, str(count))

        console.print(topics_table)
        console.print()

    # Activity Chart
    if stats["activity_by_day"]:
        console.print(Panel("[bold]Activity by Day[/bold]", style="cyan"))
        display_activity_chart(stats["activity_by_day"])
        console.print()


def display_activity_chart(activity_by_day: Dict[str, int]) -> None:
    """
    Display an ASCII bar chart of activity by day.

    Args:
        activity_by_day: Dictionary mapping date strings to session counts
    """
    if not activity_by_day:
        return

    # Sort by date
    sorted_days = sorted(activity_by_day.items())

    # Get max value for scaling
    max_count = max(activity_by_day.values())
    max_bar_width = 40

    # Display bars
    for day, count in sorted_days:
        bar_width = int((count / max_count) * max_bar_width)
        bar = "#" * bar_width  # Use # instead of █ for Windows compatibility
        console.print(f"  {day}: {bar} {count}")


def _format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}m"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
