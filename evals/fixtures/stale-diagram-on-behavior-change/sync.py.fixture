"""Sync job driven by a tiny explicit state machine: idle -> running -> idle."""

from __future__ import annotations

VALID_STATES = ("idle", "running")


class SyncJob:
    """One sync run. States: idle (waiting) and running (actively syncing)."""

    def __init__(self) -> None:
        self.state = "idle"

    def start(self) -> None:
        """idle -> running."""
        if self.state != "idle":
            raise RuntimeError(f"cannot start from {self.state!r}")
        self.state = "running"

    def finish(self) -> None:
        """running -> idle."""
        if self.state != "running":
            raise RuntimeError(f"cannot finish from {self.state!r}")
        self.state = "idle"
