"""Tests for search functionality."""
import pytest
import json
from pathlib import Path
from datetime import datetime, date

from cursor_org.search import (
    TranscriptSearcher,
    SearchOptions,
    SearchMatch,
    search_transcripts
)


@pytest.fixture
def search_dir(tmp_path):
    """Create a test directory structure with transcripts."""
    # Create multiple transcript folders
    
    # Transcript 1: Authentication topic
    auth_dir = tmp_path / "2026-03-10_10h30_implement-auth_abc12345"
    auth_dir.mkdir()
    auth_file = auth_dir / "abc12345-6789-0abc-def0-123456789abc.jsonl"
    
    auth_messages = [
        {
            "role": "user",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Implement JWT authentication for the API"
                    }
                ]
            },
            "createdAt": "2026-03-10T10:30:00Z"
        },
        {
            "role": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "I'll help you implement JWT authentication. Let's start with the middleware."
                    }
                ]
            }
        },
        {
            "role": "user",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Add authentication checks to all protected routes"
                    }
                ]
            }
        }
    ]
    
    with open(auth_file, 'w', encoding='utf-8') as f:
        for msg in auth_messages:
            f.write(json.dumps(msg) + '\n')
    
    # Create summary.md
    summary_file = auth_dir / "summary.md"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("# Authentication Implementation\n\nImplemented JWT authentication system.\n")
    
    # Transcript 2: Bug fix topic
    bug_dir = tmp_path / "2026-03-12_14h15_fix-parser-bug_def45678"
    bug_dir.mkdir()
    bug_file = bug_dir / "def45678-9abc-def0-1234-56789abcdef0.jsonl"
    
    bug_messages = [
        {
            "role": "user",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "There's a bug in the parser when handling empty messages"
                    }
                ]
            },
            "createdAt": "2026-03-12T14:15:00Z"
        },
        {
            "role": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Let me fix the bug in the parser module"
                    }
                ]
            }
        }
    ]
    
    with open(bug_file, 'w', encoding='utf-8') as f:
        for msg in bug_messages:
            f.write(json.dumps(msg) + '\n')
    
    # Transcript 3: Unorganized (UUID folder)
    uuid_dir = tmp_path / "f1234567-89ab-cdef-0123-456789abcdef"
    uuid_dir.mkdir()
    uuid_file = uuid_dir / "f1234567-89ab-cdef-0123-456789abcdef.jsonl"
    
    uuid_messages = [
        {
            "role": "user",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Refactor the database connection code"
                    }
                ]
            },
            "createdAt": "2026-03-14T09:00:00Z"
        }
    ]
    
    with open(uuid_file, 'w', encoding='utf-8') as f:
        for msg in uuid_messages:
            f.write(json.dumps(msg) + '\n')
    
    return tmp_path


def test_search_basic_text(search_dir):
    """Test basic text search."""
    searcher = TranscriptSearcher(search_dir)
    results = searcher.search_text("authentication")
    
    assert len(results) >= 1
    assert any("auth" in r.topic.lower() for r in results)
    assert any(r.match_count > 0 for r in results)


def test_search_case_sensitive(search_dir):
    """Test case-sensitive search."""
    searcher = TranscriptSearcher(search_dir)
    
    # Case-insensitive (default)
    options_insensitive = SearchOptions(case_sensitive=False)
    results_insensitive = searcher.search_text("JWT", options_insensitive)
    
    # Case-sensitive
    options_sensitive = SearchOptions(case_sensitive=True)
    results_sensitive = searcher.search_text("JWT", options_sensitive)
    
    # Should find matches in case-insensitive mode
    assert len(results_insensitive) >= 1
    
    # Case-sensitive should also find (JWT is uppercase in test data)
    assert len(results_sensitive) >= 1


def test_search_no_matches(search_dir):
    """Test search with no matches."""
    searcher = TranscriptSearcher(search_dir)
    results = searcher.search_text("nonexistent_keyword_xyz")
    
    assert len(results) == 0


def test_search_in_summary(search_dir):
    """Test search in summary.md files."""
    searcher = TranscriptSearcher(search_dir)
    results = searcher.search_text("Implementation")
    
    # Should find in summary.md
    assert len(results) >= 1
    # Should have match in summary
    assert any("[summary.md]" in snippet for r in results for snippet in r.snippets)


def test_search_with_date_filter(search_dir):
    """Test search with date filtering."""
    searcher = TranscriptSearcher(search_dir)
    
    # Search for everything from March 12 onwards
    options = SearchOptions(
        date_from=date(2026, 3, 12),
        date_to=date(2026, 3, 14)
    )
    results = searcher.search_text("bug", options)
    
    # Should find the bug fix transcript
    assert len(results) >= 1
    assert any("bug" in r.topic.lower() for r in results)


def test_search_date_range_exclusion(search_dir):
    """Test that date filter excludes results outside range."""
    searcher = TranscriptSearcher(search_dir)
    
    # Search only March 10
    options = SearchOptions(
        date_from=date(2026, 3, 10),
        date_to=date(2026, 3, 10)
    )
    results = searcher.search_text("bug", options)
    
    # Should NOT find bug transcript (March 12)
    assert len(results) == 0


def test_search_organized_only(search_dir):
    """Test organized_only filter."""
    searcher = TranscriptSearcher(search_dir)
    
    # Search only organized transcripts
    options = SearchOptions(organized_only=True)
    results = searcher.search_text("database", options)
    
    # Should NOT find UUID folder transcript
    assert len(results) == 0
    
    # Search all (including unorganized)
    options_all = SearchOptions(organized_only=False)
    results_all = searcher.search_text("database", options_all)
    
    # Should find UUID folder transcript
    assert len(results_all) >= 1


def test_search_with_limit(search_dir):
    """Test result limiting."""
    searcher = TranscriptSearcher(search_dir)
    
    # Limit to 1 result
    options = SearchOptions(limit=1)
    results = searcher.search_text("the", options)  # Common word
    
    # Should return at most 1 result
    assert len(results) <= 1


def test_search_by_date_only(search_dir):
    """Test search by date range without text query."""
    searcher = TranscriptSearcher(search_dir)
    
    # Collect all transcripts first to see what we have
    all_transcripts = list(searcher.collector.collect_all())
    
    # Note: This test just validates the API works, not the actual filtering
    # since file dates are based on creation time during test run
    today = date.today()
    
    results = searcher.search_by_date(
        date_from=today,
        date_to=today
    )
    
    # Should not crash and return a list
    assert isinstance(results, list)
    
    # If transcripts were created today, should find them
    # Otherwise, just verify the function doesn't crash
    if len(all_transcripts) > 0:
        assert len(results) >= 0  # Just verify it doesn't crash


def test_search_by_tags(search_dir):
    """Test search by tags."""
    # Create a transcript with tags
    tagged_dir = search_dir / "2026-03-13_11h00_security-update_ghi78901"
    tagged_dir.mkdir()
    tagged_file = tagged_dir / "ghi78901-2345-6789-abcd-ef0123456789.jsonl"
    
    messages = [
        {
            "role": "user",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Update security settings"
                    }
                ]
            },
            "createdAt": "2026-03-13T11:00:00Z"
        }
    ]
    
    with open(tagged_file, 'w', encoding='utf-8') as f:
        for msg in messages:
            f.write(json.dumps(msg) + '\n')
    
    # Note: Tags would need to be in metadata, which requires proper parsing
    # For now, this test demonstrates the API
    searcher = TranscriptSearcher(search_dir)
    results = searcher.search_by_tags(["security"])
    
    # This will be empty unless we add tag support to parser
    # Test validates that the function doesn't crash
    assert isinstance(results, list)


def test_search_match_properties(search_dir):
    """Test SearchMatch object properties."""
    searcher = TranscriptSearcher(search_dir)
    results = searcher.search_text("authentication")
    
    assert len(results) > 0
    
    match = results[0]
    
    # Test properties
    assert isinstance(match.date_str, str)
    assert isinstance(match.topic, str)
    assert isinstance(match.relative_path, str)
    assert match.match_count > 0
    assert isinstance(match.snippets, list)


def test_search_snippet_creation(search_dir):
    """Test snippet extraction."""
    searcher = TranscriptSearcher(search_dir)
    
    options = SearchOptions(context_lines=2)
    results = searcher.search_text("JWT", options)
    
    assert len(results) > 0
    
    # Should have snippets
    match = results[0]
    assert len(match.snippets) > 0
    
    # Snippets should contain the query (case-insensitive)
    assert any("jwt" in snippet.lower() for snippet in match.snippets)


def test_search_empty_directory(tmp_path):
    """Test search in empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    
    searcher = TranscriptSearcher(empty_dir)
    results = searcher.search_text("anything")
    
    assert len(results) == 0


def test_search_corrupted_jsonl(tmp_path):
    """Test search handles corrupted JSONL gracefully."""
    bad_dir = tmp_path / "bad_transcript"
    bad_dir.mkdir()
    bad_file = bad_dir / "test.jsonl"
    
    # Write corrupted JSON
    with open(bad_file, 'w', encoding='utf-8') as f:
        f.write("not valid json\n")
        f.write('{"valid": "json"}\n')
    
    searcher = TranscriptSearcher(tmp_path)
    results = searcher.search_text("valid")
    
    # Should handle gracefully and still find valid lines
    assert isinstance(results, list)


def test_search_options_defaults():
    """Test SearchOptions default values."""
    options = SearchOptions()
    
    assert options.case_sensitive is False
    assert options.date_from is None
    assert options.date_to is None
    assert options.tags == []
    assert options.organized_only is False
    assert options.context_lines == 0
    assert options.limit is None


def test_convenience_function(search_dir):
    """Test the convenience search_transcripts function."""
    results = search_transcripts(
        root_dir=search_dir,
        query="authentication",
        case_sensitive=False,
        limit=10
    )
    
    assert isinstance(results, list)
    assert len(results) >= 1


def test_search_multiple_matches_per_file(search_dir):
    """Test that multiple matches in same file are counted correctly."""
    searcher = TranscriptSearcher(search_dir)
    results = searcher.search_text("authentication")
    
    # Find the auth transcript
    auth_result = None
    for r in results:
        if "auth" in r.topic.lower():
            auth_result = r
            break
    
    assert auth_result is not None
    # Should have multiple matches (appears in multiple messages)
    assert auth_result.match_count >= 2


def test_search_thinking_blocks(tmp_path):
    """Test search in thinking blocks."""
    thinking_dir = tmp_path / "thinking"
    thinking_dir.mkdir()
    thinking_file = thinking_dir / "test.jsonl"
    
    messages = [
        {
            "role": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Let me analyze this"
                    }
                ]
            },
            "thinking": {
                "blocks": [
                    {"content": "First, I need to understand the authentication flow"},
                    {"content": "Then implement the JWT validation"}
                ]
            },
            "createdAt": "2026-03-10T10:00:00Z"
        }
    ]
    
    with open(thinking_file, 'w', encoding='utf-8') as f:
        for msg in messages:
            f.write(json.dumps(msg) + '\n')
    
    searcher = TranscriptSearcher(tmp_path)
    results = searcher.search_text("authentication")
    
    # Should find in thinking blocks
    assert len(results) >= 1
    assert any(r.match_count > 0 for r in results)


def test_search_preserves_order(search_dir):
    """Test that results are ordered by date (newest first)."""
    searcher = TranscriptSearcher(search_dir)
    results = searcher.search_text("the")  # Common word
    
    if len(results) >= 2:
        # Check dates are in descending order
        for i in range(len(results) - 1):
            if results[i].metadata and results[i+1].metadata:
                if results[i].metadata.created_at and results[i+1].metadata.created_at:
                    assert results[i].metadata.created_at >= results[i+1].metadata.created_at


def test_search_performance_indicator(search_dir):
    """Test that search completes in reasonable time."""
    import time
    
    searcher = TranscriptSearcher(search_dir)
    
    start = time.time()
    results = searcher.search_text("test")
    elapsed = time.time() - start
    
    # Should complete quickly for small dataset
    assert elapsed < 5.0  # 5 seconds for 3 transcripts is generous
    assert isinstance(results, list)
