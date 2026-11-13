from __future__ import annotations

import asyncio
import inspect
import logging
import os
import signal
from typing import Any, Callable, Coroutine, List, Optional, Set

from app.core.config import settings

logger = logging.getLogger("ruby.agent.cancellation")


class ProcessGroupManager:
    """
    Tracks and terminates spawned subprocesses and their entire child process trees.
    Uses POSIX process groups (os.killpg) with graceful SIGTERM and forceful SIGKILL escalation.
    """

    _active_pids: Set[int] = set()

    @classmethod
    def register_pid(cls, pid: int) -> None:
        cls._active_pids.add(pid)

    @classmethod
    def unregister_pid(cls, pid: int) -> None:
        cls._active_pids.discard(pid)

    @classmethod
    async def terminate_process_group(
        cls,
        pid: int,
        grace_period: Optional[float] = None,
    ) -> bool:
        """
        Terminates the process group rooted at pid.
        Sends SIGTERM first, waits up to grace_period, then escalates to SIGKILL.
        """
        cls._active_pids.discard(pid)
        grace = grace_period if grace_period is not None else settings.agent_cancellation_grace_period_seconds

        if not hasattr(os, "killpg") or not hasattr(os, "getpgid"):
            # Non-posix fallback
            try:
                os.kill(pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            return True

        try:
            pgid = os.getpgid(pid)
        except (ProcessLookupError, PermissionError):
            return True  # Process already exited

        # Send SIGTERM to process group
        try:
            os.killpg(pgid, signal.SIGTERM)
            logger.info("Sent SIGTERM to process group %d (pid %d)", pgid, pid)
        except (ProcessLookupError, PermissionError):
            return True

        # Wait for processes to exit cooperatively within grace period
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < grace:
            try:
                os.killpg(pgid, 0)  # Check if any process in pgid is alive
                await asyncio.sleep(0.1)
            except ProcessLookupError:
                logger.info("Process group %d cleanly terminated after SIGTERM", pgid)
                return True
            except PermissionError:
                break

        # If still alive, escalate to SIGKILL
        try:
            os.killpg(pgid, signal.SIGKILL)
            logger.warning("Forcefully killed process group %d with SIGKILL after grace period", pgid)
        except (ProcessLookupError, PermissionError):
            pass

        return True

    @classmethod
    async def terminate_all_active(cls) -> None:
        """Reaps all currently registered active subprocess groups."""
        pids = list(cls._active_pids)
        for pid in pids:
            await cls.terminate_process_group(pid)


class CancellationToken:
    """
    Cooperative cancellation token passed through agent execution loops and tool dispatches.
    Allows registering cleanup hooks and ensures process termination on user stop.
    """

    def __init__(self, grace_period_seconds: Optional[float] = None):
        self._is_cancelled = False
        self._grace_period_seconds = (
            grace_period_seconds
            if grace_period_seconds is not None
            else settings.agent_cancellation_grace_period_seconds
        )
        self._callbacks: List[Callable[[], Any]] = []
        self._associated_pids: Set[int] = set()

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled

    @property
    def grace_period_seconds(self) -> float:
        return self._grace_period_seconds

    def check_cancelled(self) -> None:
        if self._is_cancelled:
            raise asyncio.CancelledError("Operation was cancelled by user or system.")

    def register_callback(self, callback: Callable[[], Any]) -> None:
        """Registers a synchronous or asynchronous callback to run upon cancellation."""
        self._callbacks.append(callback)

    def attach_pid(self, pid: int) -> None:
        """Attaches a child process PID to be reaped when this token is cancelled."""
        self._associated_pids.add(pid)
        ProcessGroupManager.register_pid(pid)

    def detach_pid(self, pid: int) -> None:
        self._associated_pids.discard(pid)
        ProcessGroupManager.unregister_pid(pid)

    async def cancel(self) -> None:
        """
        Triggers cancellation:
        1. Marks token as cancelled.
        2. Executes registered callbacks.
        3. Terminates all attached process groups with cooperative grace period.
        """
        if self._is_cancelled:
            return

        self._is_cancelled = True
        logger.info("CancellationToken triggered: cleaning up callbacks and subprocesses")

        # Execute registered callbacks
        for cb in self._callbacks:
            try:
                res = cb()
                if inspect.isawaitable(res):
                    await res
            except Exception as e:
                logger.warning("Error in cancellation callback: %s", e)

        # Terminate all attached process groups
        for pid in list(self._associated_pids):
            await ProcessGroupManager.terminate_process_group(
                pid, grace_period=self._grace_period_seconds
            )
        self._associated_pids.clear()
