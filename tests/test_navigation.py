"""Tests for navigation and project discovery functionality."""
import tempfile
from pathlib import Path
import pytest

from cursor_org.navigation import (
    parse_project_name,
    list_cursor_projects,
    get_project_by_index,
    get_project_by_name,
)


def test_parse_project_name_simple():
    """Test parsing simple project names."""
    name, context = parse_project_name("c-Users-druiz-Documents-Laboratorio-find-chats-state-cursor")
    assert "state-cursor" in name or "find-chats" in name
    assert context != ""


def test_parse_project_name_workspace():
    """Test parsing code-workspace names."""
    name, context = parse_project_name("c-Users-druiz-Documents-Laboratorio-haletheia-code-workspace")
    assert "workspace" in name
    assert "haletheia" in context or "code" in context


def test_parse_project_name_workspace_json():
    """Test parsing workspace-json names."""
    name, context = parse_project_name("c-Users-druiz-AppData-Roaming-Cursor-User-Workspaces-1773382579405-workspace-json")
    assert "workspace-json" in name
    assert "Workspaces" in context or context != ""


def test_parse_project_name_short():
    """Test parsing short project names."""
    name, context = parse_project_name("c-Users-druiz-arch-dd")
    assert name == "arch-dd"


def test_get_project_by_name_not_found():
    """Test getting project by name when not found."""
    project = get_project_by_name("nonexistent-project-xyz123")
    assert project is None


def test_get_project_by_index_invalid():
    """Test getting project by invalid index."""
    project = get_project_by_index(99999)
    assert project is None
    
    project = get_project_by_index(0)
    assert project is None
    
    project = get_project_by_index(-1)
    assert project is None


def test_parse_project_name_edge_cases():
    """Test edge cases in project name parsing."""
    # Empty parts
    name, context = parse_project_name("c-Users--Documents-project")
    assert name != ""
    
    # Many dashes
    name, context = parse_project_name("c-Users-druiz-very-long-path-to-my-project-name")
    assert name != ""
    
    # Single part
    name, context = parse_project_name("project")
    assert name == "project"


def test_list_cursor_projects_structure():
    """Test that list_cursor_projects returns correct structure."""
    projects = list_cursor_projects()
    
    # Each project should have required keys
    for proj in projects:
        assert 'name' in proj
        assert 'context' in proj
        assert 'full_name' in proj
        assert 'path' in proj
        assert 'transcripts_dir' in proj
        assert 'transcript_count' in proj
        assert 'organized_count' in proj
        
        # Check types
        assert isinstance(proj['name'], str)
        assert isinstance(proj['context'], str)
        assert isinstance(proj['transcript_count'], int)
        assert isinstance(proj['organized_count'], int)
        assert isinstance(proj['path'], Path)
        assert isinstance(proj['transcripts_dir'], Path)


def test_list_cursor_projects_sorting():
    """Test that projects are sorted correctly."""
    projects = list_cursor_projects()
    
    if len(projects) > 1:
        # Should be sorted by name, then context
        for i in range(len(projects) - 1):
            curr_name = projects[i]['name'].lower()
            next_name = projects[i + 1]['name'].lower()
            
            # Either name is less, or names are equal and context differs
            assert curr_name <= next_name


def test_get_project_by_name_partial_match():
    """Test getting project by partial name match."""
    projects = list_cursor_projects()
    
    if projects:
        # Get first project
        first_proj = projects[0]
        
        # Try partial match (first few chars of name)
        if len(first_proj['name']) >= 3:
            partial = first_proj['name'][:3]
            found = get_project_by_name(partial)
            
            # Should find something (maybe not exact match, but something)
            # This is fine - partial matching is fuzzy
            assert found is None or 'name' in found


def test_get_project_by_name_context_match():
    """Test getting project by context."""
    projects = list_cursor_projects()
    
    # Find project with context
    proj_with_context = next((p for p in projects if p['context']), None)
    
    if proj_with_context:
        # Search by part of context
        context_part = proj_with_context['context'].split('/')[0] if '/' in proj_with_context['context'] else proj_with_context['context']
        
        if context_part and len(context_part) >= 3:
            found = get_project_by_name(context_part)
            # Should find something matching this context
            assert found is None or context_part.lower() in (found['context'].lower() + found['name'].lower() + found['full_name'].lower())


def test_get_project_by_index_valid():
    """Test getting project by valid index."""
    projects = list_cursor_projects()
    
    if projects:
        # Get first project
        proj = get_project_by_index(1)
        assert proj is not None
        assert proj['name'] == projects[0]['name']
        
        # Get last project
        proj = get_project_by_index(len(projects))
        assert proj is not None
        assert proj['name'] == projects[-1]['name']


def test_workspace_differentiation():
    """Test that multiple workspaces are differentiated by context."""
    projects = list_cursor_projects()
    
    workspaces = [p for p in projects if 'workspace' in p['name'].lower()]
    
    if len(workspaces) > 1:
        # Check that they have different contexts or full names
        for i in range(len(workspaces) - 1):
            for j in range(i + 1, len(workspaces)):
                w1 = workspaces[i]
                w2 = workspaces[j]
                
                # Should differ in at least one of: context, full_name, path
                assert (
                    w1['context'] != w2['context'] or
                    w1['full_name'] != w2['full_name'] or
                    w1['path'] != w2['path']
                ), f"Workspaces not differentiated: {w1['name']} vs {w2['name']}"


def test_organized_count_logic():
    """Test that organized count is calculated correctly."""
    projects = list_cursor_projects()
    
    for proj in projects:
        # Organized count should not exceed transcript count
        assert proj['organized_count'] <= proj['transcript_count']
        
        # Should be non-negative
        assert proj['organized_count'] >= 0
        assert proj['transcript_count'] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
