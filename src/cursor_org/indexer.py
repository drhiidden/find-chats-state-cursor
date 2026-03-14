"""
AITS Index Generator

Generates index.json files according to AITS v1.0 specification.
The index provides fast search without parsing all transcripts.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from .parser import TranscriptParser
from .models import TranscriptMetadata


class TranscriptIndexer:
    """Generates and manages AITS v1.0 compliant index files."""
    
    def __init__(self, transcripts_dir: Path):
        """Initialize indexer for a transcripts directory.
        
        Args:
            transcripts_dir: Root directory containing transcripts
                            (e.g., .aichats/ or agent-transcripts/)
        """
        self.transcripts_dir = Path(transcripts_dir)
        self.index_path = self.transcripts_dir / "index.json"
    
    def generate_index(self, force_regenerate: bool = False) -> Dict[str, Any]:
        """Generate or update the index.json file.
        
        Args:
            force_regenerate: If True, regenerate entire index from scratch.
                            If False, try to update incrementally.
        
        Returns:
            The generated index as a dictionary
        """
        # Load existing index if available
        existing_index = None
        if not force_regenerate and self.index_path.exists():
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    existing_index = json.load(f)
            except (json.JSONDecodeError, IOError):
                # Corrupted index, regenerate
                existing_index = None
        
        # Find all transcript files
        transcript_files = list(self.transcripts_dir.rglob("*.jsonl"))
        
        # Build index entries
        entries = []
        for transcript_file in transcript_files:
            try:
                # Check if we can reuse existing entry
                if existing_index and not force_regenerate:
                    existing_entry = self._find_existing_entry(
                        existing_index, transcript_file
                    )
                    if existing_entry and self._is_entry_current(
                        existing_entry, transcript_file
                    ):
                        entries.append(existing_entry)
                        continue
                
                # Parse transcript to extract metadata
                parser = TranscriptParser(transcript_file)
                metadata = parser.parse()
                
                # Create index entry
                entry = self._create_index_entry(metadata, transcript_file)
                entries.append(entry)
                
            except Exception as e:
                # Log error but continue indexing other files
                print(f"Warning: Failed to index {transcript_file}: {e}")
                continue
        
        # Build complete index structure
        index = {
            "aits_index_version": "1.0.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_transcripts": len(entries),
            "transcripts": entries
        }
        
        # Write index file
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        return index
    
    def _create_index_entry(
        self, 
        metadata: TranscriptMetadata, 
        file_path: Path
    ) -> Dict[str, Any]:
        """Create an index entry for a transcript.
        
        Index entries contain summary information for fast search.
        """
        # Calculate relative path from transcripts_dir
        try:
            rel_path = file_path.relative_to(self.transcripts_dir)
        except ValueError:
            # File is outside transcripts_dir, use absolute path
            rel_path = file_path
        
        entry = {
            "id": metadata.uuid,
            "title": metadata.title,
            "created_at": metadata.created_at.isoformat() if metadata.created_at else None,
            "updated_at": metadata.updated_at.isoformat() if metadata.updated_at else None,
            "status": metadata.status or "active",
            "path": str(rel_path).replace("\\", "/"),  # Normalize to forward slashes
            "message_count": metadata.message_count,
            "compressed": str(file_path).endswith(".gz")
        }
        
        # Add optional fields if present
        if metadata.model:
            entry["model"] = metadata.model
        if metadata.tags:
            entry["tags"] = metadata.tags
        if metadata.languages:
            entry["languages"] = metadata.languages
        if metadata.mode:
            entry["mode"] = metadata.mode
        if metadata.outcome:
            entry["outcome"] = metadata.outcome
        
        return entry
    
    def _find_existing_entry(
        self, 
        existing_index: Dict, 
        file_path: Path
    ) -> Optional[Dict]:
        """Find existing entry for a transcript file."""
        file_id = file_path.stem  # UUID from filename
        
        for entry in existing_index.get("transcripts", []):
            if entry.get("id") == file_id:
                return entry
        
        return None
    
    def _is_entry_current(self, entry: Dict, file_path: Path) -> bool:
        """Check if an index entry is still current (file hasn't changed)."""
        try:
            # Check if file modification time matches entry updated_at
            file_mtime = datetime.fromtimestamp(
                file_path.stat().st_mtime, 
                tz=timezone.utc
            )
            
            entry_updated = entry.get("updated_at")
            if not entry_updated:
                return False
            
            entry_mtime = datetime.fromisoformat(entry_updated)
            
            # Allow 1 second tolerance for filesystem timestamp precision
            return abs((file_mtime - entry_mtime).total_seconds()) < 1
            
        except (OSError, ValueError):
            return False
    
    def search_index(
        self, 
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        languages: Optional[List[str]] = None,
        status: Optional[str] = None,
        model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search the index with various filters.
        
        Args:
            query: Text query to search in titles
            tags: Filter by tags (any match)
            languages: Filter by programming languages (any match)
            status: Filter by status (exact match)
            model: Filter by AI model (exact match)
        
        Returns:
            List of matching index entries
        """
        if not self.index_path.exists():
            return []
        
        with open(self.index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        results = index.get("transcripts", [])
        
        # Apply filters
        if query:
            query_lower = query.lower()
            results = [
                t for t in results 
                if query_lower in t.get("title", "").lower()
            ]
        
        if tags:
            results = [
                t for t in results
                if any(tag in t.get("tags", []) for tag in tags)
            ]
        
        if languages:
            results = [
                t for t in results
                if any(lang in t.get("languages", []) for lang in languages)
            ]
        
        if status:
            results = [t for t in results if t.get("status") == status]
        
        if model:
            results = [t for t in results if t.get("model") == model]
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics from the index.
        
        Returns summary statistics like total transcripts, languages used,
        most common tags, etc.
        """
        if not self.index_path.exists():
            return {
                "total": 0,
                "by_status": {},
                "by_language": {},
                "by_tag": {},
                "by_model": {}
            }
        
        with open(self.index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        transcripts = index.get("transcripts", [])
        
        # Count by various dimensions
        by_status = {}
        by_language = {}
        by_tag = {}
        by_model = {}
        
        for t in transcripts:
            # Status
            status = t.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1
            
            # Languages
            for lang in t.get("languages", []):
                by_language[lang] = by_language.get(lang, 0) + 1
            
            # Tags
            for tag in t.get("tags", []):
                by_tag[tag] = by_tag.get(tag, 0) + 1
            
            # Model
            model = t.get("model", "unknown")
            by_model[model] = by_model.get(model, 0) + 1
        
        return {
            "total": len(transcripts),
            "by_status": by_status,
            "by_language": dict(sorted(by_language.items(), key=lambda x: x[1], reverse=True)),
            "by_tag": dict(sorted(by_tag.items(), key=lambda x: x[1], reverse=True)),
            "by_model": by_model
        }


def generate_index(transcripts_dir: Path, force: bool = False) -> Dict[str, Any]:
    """Convenience function to generate an index.
    
    Args:
        transcripts_dir: Directory containing transcripts
        force: Force regeneration from scratch
    
    Returns:
        The generated index
    """
    indexer = TranscriptIndexer(transcripts_dir)
    return indexer.generate_index(force_regenerate=force)
