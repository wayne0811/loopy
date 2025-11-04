"""Tests for CLI module."""

import pytest
import tempfile
from click.testing import CliRunner
from loopy.cli import main


@pytest.fixture
def db_path():
    """Create a temporary database path for testing."""
    with tempfile.NamedTemporaryFile() as f:
        db_path = f.name
        yield db_path


def test_list_empty(db_path, monkeypatch):
    """Test listing when no loops exist."""
    monkeypatch.setenv("LOOPY_DB", db_path)

    runner = CliRunner()
    result = runner.invoke(main, ["list"])

    assert result.exit_code == 0
    assert "No loops found" in result.output


def test_create_command(db_path, monkeypatch):
    """Test creating a loop."""
    monkeypatch.setenv("LOOPY_DB", db_path)

    runner = CliRunner()
    result = runner.invoke(
        main, ["--id", "test-loop", "create", "echo {}"], input="item1\nitem2\n"
    )

    assert result.exit_code == 0
    assert "created" in result.output


def test_run_nonexistent_loop(db_path, monkeypatch):
    """Test running a non-existent loop."""
    monkeypatch.setenv("LOOPY_DB", db_path)

    runner = CliRunner()
    result = runner.invoke(main, ["--id", "nonexistent", "run"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_reset_nonexistent_loop(db_path, monkeypatch):
    """Test resetting a non-existent loop."""
    monkeypatch.setenv("LOOPY_DB", db_path)

    runner = CliRunner()
    result = runner.invoke(main, ["--id", "nonexistent", "reset"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_delete_nonexistent_loop(db_path, monkeypatch):
    """Test deleting a non-existent loop."""
    monkeypatch.setenv("LOOPY_DB", db_path)

    runner = CliRunner()
    result = runner.invoke(main, ["--id", "nonexistent", "delete"])

    assert result.exit_code == 1
    assert "not found" in result.output
