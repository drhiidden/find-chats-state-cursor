"""Tests for CLI commands."""

import pytest
from typer.testing import CliRunner
from cursor_org.cli import app

runner = CliRunner()


def test_version_command():
    """Test the version command."""
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    # Should contain either version number or development message
    assert "cursor-org" in result.stdout.lower()
    assert "version" in result.stdout.lower() or "development" in result.stdout.lower()


def test_version_command_output_format():
    """Test that version command produces clean output."""
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    # Output should not be empty
    assert len(result.stdout.strip()) > 0
