"""Legacy parser module - kept for backward compatibility.

New code should use: from cursor_org.parsers import get_parser, auto_detect_ide
"""
from pathlib import Path
from typing import Optional

from .models import TranscriptMetadata
from .parsers import get_parser, auto_detect_ide


class TranscriptParser:
    """Legacy parser class - delegates to new multi-IDE architecture.
    
    This class is kept for backward compatibility. New code should use:
        from cursor_org.parsers import get_parser
        parser = get_parser("cursor", file_path)
    """

    def __init__(self, file_path: Path, ide: Optional[str] = None):
        self.file_path = Path(file_path)
        
        # Auto-detect IDE if not specified
        if ide is None:
            ide = auto_detect_ide(self.file_path)
            if ide is None:
                ide = "cursor"  # Default fallback
        
        # Get appropriate parser
        self._parser = get_parser(ide, self.file_path)

    def parse(self) -> TranscriptMetadata:
        """Delegate to the appropriate IDE-specific parser."""
        return self._parser.parse()
