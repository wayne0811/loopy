"""Tests for Loop class."""

import pytest
import tempfile
import subprocess
from unittest.mock import patch, MagicMock
from sqlmodel import Session
from loopy.models import get_engine, ItemStatus
from loopy.loop import Loop


run_kwargs = {
    "shell": True,
    "stdout": subprocess.PIPE,
    "stderr": subprocess.STDOUT,
    "text": True,
    "universal_newlines": True,
    "start_new_session": True,
}


@pytest.fixture
def db_session():
    """Create a temporary database session for testing."""
    with tempfile.NamedTemporaryFile() as f:
        db_path = f.name
        engine = get_engine(db_path)
        with Session(engine) as session:
            yield session


def test_create_loop(db_session):
    """Test creating a loop."""
    loop = Loop.create("test-loop", "echo {}", ["item1", "item2"], db_session)

    assert loop.exists()
    loops = Loop.list_all(db_session)
    assert len(loops) == 1
    assert loops[0][0] == "test-loop"


def test_create_existing_loop_error(db_session):
    """Test creating a loop that already exists shows error."""
    Loop.create("test-loop", "echo {}", ["item1"], db_session)

    with pytest.raises(ValueError, match="Loop test-loop already exists"):
        Loop.create("test-loop", "echo {}", ["item2"], db_session)


@patch("subprocess.Popen")
def test_run_loop_success(mock_run, db_session):
    """Test running a loop successfully."""
    mock_run.return_value = MagicMock(returncode=0, stderr="")

    loop = Loop.create("test-loop", "echo {}", ["item1"], db_session)
    success = loop.run()

    assert success is True
    mock_run.assert_called_once()


@patch("subprocess.Popen")
def test_run_loop_failure(mock_run, db_session):
    """Test running a loop with failure."""
    mock_run.return_value = MagicMock(returncode=1, stderr="Command failed")

    loop = Loop.create("test-loop", "echo {}", ["item1"], db_session)
    success = loop.run()

    assert success is False


def test_reset_loop(db_session):
    """Test resetting a loop."""
    loop = Loop.create("test-loop", "echo {}", ["item1"], db_session)
    loop.reset()

    # Should still exist after reset
    assert loop.exists()


def test_delete_loop(db_session):
    """Test deleting a loop."""
    loop = Loop.create("test-loop", "echo {}", ["item1"], db_session)
    loop.delete()

    assert not loop.exists()


def test_copy_loop(db_session):
    """Test copying a loop."""
    loop = Loop.create("test-loop", "echo {}", ["item1"], db_session)
    loop.copy_to("test-loop-2")

    new_loop = Loop("test-loop-2", db_session)
    assert new_loop.exists()

    loops = Loop.list_all(db_session)
    assert len(loops) == 2


@patch("subprocess.Popen")
def test_environment_variable_assignment(mock_run, db_session):
    """Test environment variable assignment in commands."""
    mock_run.return_value = MagicMock(returncode=0, stderr="")

    loop = Loop.create("test-env", "ENV_VAR=test_value echo {}", ["item1"], db_session)
    loop.run()

    mock_run.assert_called_once_with("ENV_VAR=test_value echo item1", **run_kwargs)


def test_add_items(db_session):
    """Test adding items to existing loop."""
    loop = Loop.create("test-loop", "echo {}", ["item1"], db_session)
    loop.add_items(["item2", "item3"])

    items = loop.list_items()
    assert len(items) == 3
    assert ("item1", ItemStatus.PENDING, 0) in items
    assert ("item2", ItemStatus.PENDING, 0) in items
    assert ("item3", ItemStatus.PENDING, 0) in items


def test_replace_items(db_session):
    """Test replacing all items in loop."""
    loop = Loop.create("test-loop", "echo {}", ["item1", "item2"], db_session)
    loop.replace_items(["new1", "new2", "new3"])

    items = loop.list_items()
    assert len(items) == 3
    assert ("new1", ItemStatus.PENDING, 0) in items
    assert ("new2", ItemStatus.PENDING, 0) in items
    assert ("new3", ItemStatus.PENDING, 0) in items


def test_list_items(db_session):
    """Test listing items in loop."""
    loop = Loop.create("test-loop", "echo {}", ["item1", "item2"], db_session)

    items = loop.list_items()
    assert len(items) == 2
    assert ("item1", ItemStatus.PENDING, 0) in items
    assert ("item2", ItemStatus.PENDING, 0) in items
