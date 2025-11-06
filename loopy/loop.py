"""Loop class for executing commands."""

import subprocess
import signal
from os import killpg
from typing import List, Optional
from sqlmodel import Session, select
from .models import LoopModel, LoopItem, ItemStatus, get_session


class Loop:
    def __init__(
        self,
        loop_id: str,
        session: Optional[Session] = None,
        db_path: Optional[str] = None,
    ):
        self.loop_id = loop_id
        self.session = session or get_session(db_path)

    @classmethod
    def create(
        cls,
        loop_id: str,
        command: str,
        items: List[str],
        session: Optional[Session] = None,
        db_path: Optional[str] = None,
    ):
        """Create a new loop with items."""
        session = session or get_session(db_path)

        # Check if loop already exists
        existing = session.get(LoopModel, loop_id)
        if existing:
            raise ValueError(f"Loop {loop_id} already exists")

        loop_model = LoopModel(id=loop_id, command=command)
        session.add(loop_model)

        for item in items:
            item_model = LoopItem(loop_id=loop_id, item=item)
            session.add(item_model)

        session.commit()
        return cls(loop_id, session, db_path)

    @classmethod
    def list_all(cls, session: Optional[Session] = None, db_path: Optional[str] = None):
        """List all loops with progress."""
        session = session or get_session(db_path)
        loops = session.exec(
            select(LoopModel).order_by(LoopModel.created_at.desc())
        ).all()

        result = []
        for loop in loops:
            loop_instance = cls(loop.id, session, db_path)
            pending, failed, done, total = loop_instance.get_progress()
            result.append(
                (loop.id, loop.command, loop.status, pending, failed, done, total)
            )

        return result

    def exists(self):
        """Check if loop exists."""
        return self.session.get(LoopModel, self.loop_id) is not None

    def run(self, continue_on_failure: bool = False, timeout: Optional[int] = None):
        """Execute the loop."""
        loop_model = self.session.get(LoopModel, self.loop_id)
        if not loop_model:
            raise ValueError(f"Loop {self.loop_id} not found")

        pending_items = [
            item for item in loop_model.items if item.status == ItemStatus.PENDING
        ]

        if not pending_items:
            print(f"No pending items for loop {self.loop_id}")
            return True

        success = True
        for item_model in pending_items:
            try:
                cmd = loop_model.command.replace("{}", item_model.item)
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    universal_newlines=True,
                    start_new_session=True,
                )

                # Stream output in real-time
                for line in process.stdout:
                    print(f"{item_model.item}: {line.rstrip()}")

                process.wait()

                if process.returncode == 0:
                    item_model.status = ItemStatus.SUCCESS
                    self.session.commit()
                else:
                    item_model.status = ItemStatus.FAILED
                    item_model.attempts += 1
                    item_model.last_error = (
                        f"Command failed with exit code {process.returncode}"
                    )
                    self.session.commit()
                    success = False

                    if not continue_on_failure:
                        break

            except subprocess.TimeoutExpired:
                # Currently not used
                assert 0
                process.kill()
                error_msg = f"Command timed out after {timeout} seconds"
                item_model.status = ItemStatus.FAILED
                item_model.attempts += 1
                item_model.last_error = error_msg
                self.session.commit()
                print(f"{item_model.item}: {error_msg}")
                success = False

                if not continue_on_failure:
                    break

            except (KeyboardInterrupt, SystemExit):
                killpg(process.pid, signal.SIGTERM)
                raise

        return success

    def reset(self):
        """Reset loop to start from beginning."""
        loop_model = self.session.get(LoopModel, self.loop_id)
        if not loop_model:
            raise ValueError(f"Loop {self.loop_id} not found")

        for item in loop_model.items:
            item.status = ItemStatus.PENDING
            item.attempts = 0
            item.last_error = None

        self.session.commit()

    def delete(self):
        """Delete the loop."""
        loop_model = self.session.get(LoopModel, self.loop_id)
        if not loop_model:
            raise ValueError(f"Loop {self.loop_id} not found")

        # Items will be cascade deleted automatically
        self.session.delete(loop_model)
        self.session.commit()

    def update_command(self, command: str):
        """Update loop command."""
        loop_model = self.session.get(LoopModel, self.loop_id)
        if not loop_model:
            raise ValueError(f"Loop {self.loop_id} not found")

        loop_model.command = command
        self.session.commit()

    def copy_to(self, target_id: str):
        """Copy this loop to a new ID."""
        loop_model = self.session.get(LoopModel, self.loop_id)
        if not loop_model:
            raise ValueError(f"Loop {self.loop_id} not found")

        # Check if loop already exists
        existing = self.session.get(LoopModel, target_id)
        if existing:
            raise ValueError(f"Loop {target_id} already exists")

        # Copy loop
        new_loop = LoopModel(id=target_id, command=loop_model.command)
        self.session.add(new_loop)

        # Copy items
        for item in loop_model.items:
            new_item = LoopItem(
                loop_id=target_id,
                item=item.item,
                status=item.status,
                attempts=item.attempts,
                last_error=item.last_error,
            )
            self.session.add(new_item)

        self.session.commit()

    def add_items(self, items: List[str]):
        """Add items to existing loop."""
        for item in items:
            item_model = LoopItem(loop_id=self.loop_id, item=item)
            self.session.add(item_model)
        self.session.commit()

    def replace_items(self, items: List[str]):
        """Replace all items in loop."""
        loop_model = self.session.get(LoopModel, self.loop_id)
        if not loop_model:
            raise ValueError(f"Loop {self.loop_id} not found")

        # Delete existing items
        for item in loop_model.items:
            self.session.delete(item)

        # Add new items
        for item in items:
            item_model = LoopItem(loop_id=self.loop_id, item=item)
            self.session.add(item_model)

        self.session.commit()

    def list_items(self):
        """List items in the loop."""
        loop_model = self.session.get(LoopModel, self.loop_id)
        if not loop_model:
            return []
        return [(item.item, item.status, item.attempts) for item in loop_model.items]

    def get_progress(self):
        """Get loop progress statistics."""
        loop_model = self.session.get(LoopModel, self.loop_id)
        if not loop_model:
            return 0, 0, 0, 0

        items = loop_model.items
        pending = sum(1 for item in items if item.status == ItemStatus.PENDING)
        failed = sum(1 for item in items if item.status == ItemStatus.FAILED)
        done = sum(1 for item in items if item.status == ItemStatus.SUCCESS)
        total = len(items)

        return pending, failed, done, total
