"""Search functionality for transcript files.

Provides text-based search across transcripts (.jsonl) and summaries (.md)
with support for date and tag filtering.
"""
from pathlib import Path
from typing import List, Optional, Dict, Any, Iterator
from dataclasses import dataclass
from datetime import datetime, date
import json
import re
import logging

from .collector import TranscriptCollector, TranscriptFile, FileFilter
from .parser import TranscriptParser
from .models import TranscriptMetadata

logger = logging.getLogger(__name__)


@dataclass
class SearchMatch:
    """Represents a search match in a transcript."""
    transcript_path: Path
    metadata: Optional[TranscriptMetadata]
    match_count: int
    snippets: List[str]
    line_numbers: List[int]
    
    @property
    def date_str(self) -> str:
        """Return formatted date string."""
        if self.metadata and self.metadata.created_at:
            return self.metadata.created_at.strftime("%Y-%m-%d")
        return "Unknown"
    
    @property
    def topic(self) -> str:
        """Return topic/title."""
        if self.metadata:
            return self.metadata.title or self.metadata.topic_raw
        return "Unknown Topic"
    
    @property
    def relative_path(self) -> str:
        """Return relative path for display."""
        return str(self.transcript_path.name)


@dataclass
class SearchOptions:
    """Search configuration options."""
    case_sensitive: bool = False
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    tags: List[str] = None
    organized_only: bool = False
    context_lines: int = 0
    limit: Optional[int] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class TranscriptSearcher:
    """Search engine for transcript files.
    
    Supports:
    - Text search in .jsonl message content
    - Text search in .md summary files
    - Date range filtering
    - Tag filtering
    - Case-sensitive/insensitive search
    
    Examples:
        searcher = TranscriptSearcher(root_dir)
        
        # Simple text search
        results = searcher.search_text("authentication")
        
        # Search with filters
        options = SearchOptions(
            date_from=date(2026, 3, 1),
            date_to=date(2026, 3, 14),
            case_sensitive=True
        )
        results = searcher.search_text("JWT", options)
        
        # Search by tags
        results = searcher.search_by_tags(["security", "auth"])
    """
    
    def __init__(self, root_dir: Path, ide: Optional[str] = None):
        """Initialize searcher.
        
        Args:
            root_dir: Root directory containing transcripts
            ide: IDE type for parsing (auto-detected if None)
        """
        self.root_dir = Path(root_dir)
        self.ide = ide
        self.collector = TranscriptCollector(root_dir)
    
    def search_text(
        self,
        query: str,
        options: Optional[SearchOptions] = None
    ) -> List[SearchMatch]:
        """Search for text in transcripts.
        
        Args:
            query: Text to search for
            options: Search options (filters, case sensitivity, etc.)
            
        Returns:
            List of SearchMatch objects
        """
        if options is None:
            options = SearchOptions()
        
        results = []
        count = 0
        
        # Collect transcripts
        transcripts = list(self.collector.collect_all())
        
        # Apply organized_only filter
        if options.organized_only:
            transcripts = [
                t for t in transcripts
                if not FileFilter.is_uuid_folder(t.parent_dir)
            ]
        
        for transcript in transcripts:
            # Apply limit
            if options.limit and count >= options.limit:
                break
            
            # Search in this transcript
            match = self._search_in_transcript(transcript, query, options)
            
            if match and match.match_count > 0:
                # Apply date filter
                if options.date_from or options.date_to:
                    if not self._matches_date_filter(match, options):
                        continue
                
                # Apply tag filter
                if options.tags:
                    if not self._matches_tag_filter(match, options):
                        continue
                
                results.append(match)
                count += 1
        
        # Sort by date (newest first)
        results.sort(
            key=lambda m: m.metadata.created_at if m.metadata and m.metadata.created_at else datetime.min,
            reverse=True
        )
        
        return results
    
    def search_by_date(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> List[SearchMatch]:
        """Search transcripts by date range.
        
        Args:
            date_from: Start date (inclusive)
            date_to: End date (inclusive)
            
        Returns:
            List of SearchMatch objects (no text matches, just metadata)
        """
        options = SearchOptions(date_from=date_from, date_to=date_to)
        
        results = []
        transcripts = list(self.collector.collect_all())
        
        for transcript in transcripts:
            # Parse metadata
            try:
                parser = TranscriptParser(transcript.path, ide=self.ide)
                metadata = parser.parse()
            except Exception as e:
                logger.warning(f"Failed to parse {transcript.path}: {e}")
                continue
            
            # Create match (no text search)
            match = SearchMatch(
                transcript_path=transcript.path,
                metadata=metadata,
                match_count=0,
                snippets=[],
                line_numbers=[]
            )
            
            if self._matches_date_filter(match, options):
                results.append(match)
        
        # Sort by date
        results.sort(
            key=lambda m: m.metadata.created_at if m.metadata and m.metadata.created_at else datetime.min,
            reverse=True
        )
        
        return results
    
    def search_by_tags(self, tags: List[str]) -> List[SearchMatch]:
        """Search transcripts by tags.
        
        Args:
            tags: List of tags to search for (OR logic)
            
        Returns:
            List of SearchMatch objects
        """
        options = SearchOptions(tags=tags)
        
        results = []
        transcripts = list(self.collector.collect_all())
        
        for transcript in transcripts:
            # Parse metadata
            try:
                parser = TranscriptParser(transcript.path, ide=self.ide)
                metadata = parser.parse()
            except Exception as e:
                logger.warning(f"Failed to parse {transcript.path}: {e}")
                continue
            
            # Create match
            match = SearchMatch(
                transcript_path=transcript.path,
                metadata=metadata,
                match_count=0,
                snippets=[],
                line_numbers=[]
            )
            
            if self._matches_tag_filter(match, options):
                results.append(match)
        
        return results
    
    def _search_in_transcript(
        self,
        transcript: TranscriptFile,
        query: str,
        options: SearchOptions
    ) -> Optional[SearchMatch]:
        """Search for query in a single transcript."""
        snippets = []
        line_numbers = []
        match_count = 0
        
        # Compile regex pattern
        flags = 0 if options.case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(re.escape(query), flags)
        except re.error:
            logger.warning(f"Invalid regex pattern: {query}")
            return None
        
        # Parse metadata first
        metadata = None
        try:
            parser = TranscriptParser(transcript.path, ide=self.ide)
            metadata = parser.parse()
        except Exception as e:
            logger.warning(f"Failed to parse {transcript.path}: {e}")
        
        # Search in .jsonl file
        try:
            with open(transcript.path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, start=1):
                    try:
                        data = json.loads(line)
                        # Extract text content from message
                        text = self._extract_text_from_message(data)
                        
                        if pattern.search(text):
                            match_count += 1
                            line_numbers.append(line_num)
                            
                            # Extract snippet with context
                            snippet = self._create_snippet(
                                text, query, options.context_lines
                            )
                            snippets.append(snippet)
                    
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            logger.warning(f"Error reading {transcript.path}: {e}")
        
        # Also search in summary.md if it exists
        summary_path = transcript.parent_dir / "summary.md"
        if summary_path.exists():
            try:
                with open(summary_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if pattern.search(content):
                        match_count += 1
                        snippet = self._create_snippet(
                            content, query, options.context_lines
                        )
                        snippets.append(f"[summary.md] {snippet}")
            except Exception as e:
                logger.warning(f"Error reading {summary_path}: {e}")
        
        if match_count > 0 or metadata:
            return SearchMatch(
                transcript_path=transcript.path,
                metadata=metadata,
                match_count=match_count,
                snippets=snippets[:5],  # Limit snippets
                line_numbers=line_numbers[:5]
            )
        
        return None
    
    def _extract_text_from_message(self, message_data: Dict[str, Any]) -> str:
        """Extract text content from a message object."""
        text_parts = []
        
        # Extract from message.content
        if 'message' in message_data:
            message = message_data['message']
            if isinstance(message, dict) and 'content' in message:
                content = message['content']
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            text_parts.append(item.get('text', ''))
                elif isinstance(content, str):
                    text_parts.append(content)
        
        # Extract from thinking blocks
        if 'thinking' in message_data:
            thinking = message_data['thinking']
            if isinstance(thinking, dict) and 'blocks' in thinking:
                for block in thinking['blocks']:
                    if isinstance(block, dict):
                        text_parts.append(block.get('content', ''))
        
        return ' '.join(text_parts)
    
    def _create_snippet(
        self,
        text: str,
        query: str,
        context_lines: int
    ) -> str:
        """Create a snippet showing match context."""
        # Find the query in text
        query_lower = query.lower()
        text_lower = text.lower()
        
        idx = text_lower.find(query_lower)
        if idx == -1:
            # Fallback to regex
            return text[:100] + "..."
        
        # Extract context around match
        start = max(0, idx - 50)
        end = min(len(text), idx + len(query) + 50)
        
        snippet = text[start:end]
        
        # Clean up whitespace
        snippet = ' '.join(snippet.split())
        
        # Add ellipsis
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet
    
    def _matches_date_filter(
        self,
        match: SearchMatch,
        options: SearchOptions
    ) -> bool:
        """Check if match passes date filter."""
        if not match.metadata or not match.metadata.created_at:
            return False
        
        match_date = match.metadata.created_at.date()
        
        if options.date_from and match_date < options.date_from:
            return False
        
        if options.date_to and match_date > options.date_to:
            return False
        
        return True
    
    def _matches_tag_filter(
        self,
        match: SearchMatch,
        options: SearchOptions
    ) -> bool:
        """Check if match passes tag filter."""
        if not options.tags:
            return True
        
        if not match.metadata or not match.metadata.tags:
            return False
        
        # OR logic: match if ANY tag matches
        return any(tag in match.metadata.tags for tag in options.tags)


def search_transcripts(
    root_dir: Path,
    query: str,
    case_sensitive: bool = False,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    tags: Optional[List[str]] = None,
    organized_only: bool = False,
    limit: Optional[int] = None,
    ide: Optional[str] = None
) -> List[SearchMatch]:
    """Convenience function for searching transcripts.
    
    Args:
        root_dir: Root directory containing transcripts
        query: Text to search for
        case_sensitive: Enable case-sensitive search
        date_from: Filter by start date
        date_to: Filter by end date
        tags: Filter by tags
        organized_only: Only search organized transcripts
        limit: Limit number of results
        ide: IDE type (auto-detected if None)
        
    Returns:
        List of SearchMatch objects
    """
    searcher = TranscriptSearcher(root_dir, ide=ide)
    
    options = SearchOptions(
        case_sensitive=case_sensitive,
        date_from=date_from,
        date_to=date_to,
        tags=tags or [],
        organized_only=organized_only,
        limit=limit
    )
    
    return searcher.search_text(query, options)
