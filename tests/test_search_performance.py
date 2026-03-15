"""Performance test for search functionality.

Creates 100+ test transcripts and measures search performance.
"""
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

from cursor_org.search import TranscriptSearcher, SearchOptions


def create_test_transcripts(base_dir: Path, count: int = 100):
    """Create test transcripts for performance testing."""
    print(f"Creating {count} test transcripts...")
    
    topics = [
        "Implement authentication",
        "Fix parser bug",
        "Refactor database code",
        "Add error handling",
        "Update documentation",
        "Optimize performance",
        "Add unit tests",
        "Implement API endpoints",
        "Fix memory leak",
        "Add logging",
    ]
    
    keywords = [
        "authentication", "JWT", "database", "API", "bug", "error",
        "test", "refactor", "performance", "optimization", "security"
    ]
    
    for i in range(count):
        # Create folder (organized format)
        date = datetime.now() - timedelta(days=i % 30)
        topic = topics[i % len(topics)]
        uuid_short = f"{i:08x}"
        
        folder_name = f"{date.strftime('%Y-%m-%d_%Hh%M')}_{topic.lower().replace(' ', '-')}_{uuid_short}"
        folder = base_dir / folder_name
        folder.mkdir(exist_ok=True)
        
        # Create transcript file
        transcript_file = folder / f"{uuid_short}-{uuid_short}-{uuid_short}-{uuid_short}.jsonl"
        
        # Create messages with various keywords
        messages = [
            {
                "role": "user",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Let's work on {topic}. We need to handle {keywords[i % len(keywords)]} properly."
                        }
                    ]
                },
                "createdAt": date.isoformat()
            },
            {
                "role": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"I'll help you with {topic}. Let me analyze the {keywords[(i+1) % len(keywords)]} situation."
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
                            "text": f"Also make sure to test the {keywords[(i+2) % len(keywords)]} functionality."
                        }
                    ]
                }
            }
        ]
        
        with open(transcript_file, 'w', encoding='utf-8') as f:
            for msg in messages:
                f.write(json.dumps(msg) + '\n')
        
        # Create summary
        summary_file = folder / "summary.md"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"# {topic}\n\n")
            f.write(f"Working on {keywords[i % len(keywords)]} related tasks.\n")
    
    print(f"Created {count} test transcripts in {base_dir}")


def benchmark_search(base_dir: Path, query: str, description: str):
    """Benchmark a search query."""
    print(f"\n{description}")
    print("-" * 60)
    
    searcher = TranscriptSearcher(base_dir)
    
    start = time.time()
    results = searcher.search_text(query)
    elapsed = time.time() - start
    
    print(f"Query: '{query}'")
    print(f"Results: {len(results)} transcripts with {sum(r.match_count for r in results)} total matches")
    print(f"Time: {elapsed:.3f} seconds")
    print(f"Speed: {len(results) / elapsed:.1f} results/sec")
    
    return elapsed, len(results)


def main():
    """Run performance tests."""
    import tempfile
    import shutil
    
    # Create temporary directory
    test_dir = Path(tempfile.mkdtemp(prefix="search_perf_"))
    
    try:
        # Create test data
        create_test_transcripts(test_dir, count=100)
        
        print("\n" + "=" * 60)
        print("PERFORMANCE BENCHMARKS")
        print("=" * 60)
        
        # Test 1: Common word (many matches)
        benchmark_search(test_dir, "the", "Test 1: Common word search")
        
        # Test 2: Specific keyword (moderate matches)
        benchmark_search(test_dir, "authentication", "Test 2: Specific keyword")
        
        # Test 3: Rare keyword (few matches)
        benchmark_search(test_dir, "optimization", "Test 3: Rare keyword")
        
        # Test 4: No matches
        benchmark_search(test_dir, "nonexistent_xyz", "Test 4: No matches")
        
        # Test 5: Case-sensitive
        print("\nTest 5: Case-sensitive search")
        print("-" * 60)
        searcher = TranscriptSearcher(test_dir)
        options = SearchOptions(case_sensitive=True)
        start = time.time()
        results = searcher.search_text("JWT", options)
        elapsed = time.time() - start
        print(f"Query: 'JWT' (case-sensitive)")
        print(f"Results: {len(results)} transcripts")
        print(f"Time: {elapsed:.3f} seconds")
        
        # Test 6: With filters
        print("\nTest 6: Search with date filter")
        print("-" * 60)
        from datetime import date
        options = SearchOptions(
            date_from=date.today() - timedelta(days=7),
            date_to=date.today()
        )
        start = time.time()
        results = searcher.search_text("test", options)
        elapsed = time.time() - start
        print(f"Query: 'test' (last 7 days)")
        print(f"Results: {len(results)} transcripts")
        print(f"Time: {elapsed:.3f} seconds")
        
        print("\n" + "=" * 60)
        print("PERFORMANCE REQUIREMENTS CHECK")
        print("=" * 60)
        
        # Verify performance requirements
        searcher = TranscriptSearcher(test_dir)
        start = time.time()
        results = searcher.search_text("authentication")
        elapsed = time.time() - start
        
        print(f"\nSearch 100 transcripts for 'authentication':")
        print(f"  Time: {elapsed:.3f}s")
        print(f"  Requirement: < 5s for 100 transcripts")
        
        if elapsed < 5.0:
            print(f"  Status: PASSED ({elapsed:.1f}s < 5.0s)")
        else:
            print(f"  Status: FAILED ({elapsed:.1f}s >= 5.0s)")
        
        # Estimate for 1000 transcripts
        estimated_1000 = elapsed * 10
        print(f"\nEstimated time for 1000 transcripts: {estimated_1000:.1f}s")
        print(f"  Requirement: < 30s for 1000 transcripts")
        
        if estimated_1000 < 30.0:
            print(f"  Status: LIKELY TO PASS")
        else:
            print(f"  Status: MAY NEED OPTIMIZATION")
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total transcripts tested: 100")
        print(f"Average search time: {elapsed:.3f}s")
        print(f"Performance: {'EXCELLENT' if elapsed < 2 else 'GOOD' if elapsed < 5 else 'ACCEPTABLE'}")
        
    finally:
        # Cleanup
        print(f"\nCleaning up test directory: {test_dir}")
        shutil.rmtree(test_dir)
        print("Done!")


if __name__ == "__main__":
    main()
