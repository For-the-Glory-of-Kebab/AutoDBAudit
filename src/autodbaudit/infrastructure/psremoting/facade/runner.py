"""
Parallel runner for PS remoting tasks with prefixed logging.

Each server/task runs in a worker thread; logs are prefixed with the
server name and funneled through a single printer to avoid interleaving.
"""

from __future__ import annotations

# pylint: disable=line-too-long

import concurrent.futures
import logging
import queue
import threading
import time
from pathlib import Path
from typing import Callable, Iterable, Any, Optional

from .base import PSRemotingFacade

logger = logging.getLogger(__name__)


class ParallelRunner:
    """
    Execute per-server PS remoting tasks in parallel with clean console output.
    """

    COLORS = [
        "\033[95m",  # magenta
        "\033[94m",  # blue
        "\033[96m",  # cyan
        "\033[92m",  # green
        "\033[93m",  # yellow
        "\033[91m",  # red
    ]
    RESET = "\033[0m"
    ICONS = {"start": "🚀", "done": "✅", "fail": "❌"}

    def __init__(self, max_workers: int = 4, log_dir: Optional[str] = None) -> None:
        self.max_workers = max_workers
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._stop_event = threading.Event()
        self._printer = threading.Thread(target=self._log_consumer, daemon=True)
        self._color_map: dict[str, str] = {}
        self._log_dir = Path(log_dir) if log_dir else None
        if self._log_dir:
            self._log_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        items: Iterable[tuple[str, Callable[[PSRemotingFacade], Any]]],
    ) -> list[Any]:
        """
        Run tasks in parallel.

        Args:
            items: iterable of (server_name, work_fn), where work_fn takes a PSRemotingFacade and returns a result.

        Returns:
            list of results in completion order.
        """
        results: list[Any] = []
        self._printer.start()
        facade = PSRemotingFacade()

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(self._run_single, server, work_fn, facade): server
                for server, work_fn in items
            }
            for future in concurrent.futures.as_completed(futures):
                server = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:  # pylint: disable=broad-except
                    msg = f"{self.ICONS['fail']} FAILED: {exc}"
                    self._enqueue(self._fmt(server, msg, color=self._color(server)))
                    self._write_log(server, msg)

        self._stop_event.set()
        self._printer.join(timeout=2)
        return results

    def _run_single(
        self,
        server: str,
        work_fn: Callable[[PSRemotingFacade], Any],
        facade: PSRemotingFacade,
    ) -> Any:
        """Execute a single work item and route logs."""
        try:
            self._enqueue(self._fmt(server, f"{self.ICONS['start']} START", color=self._color(server)))
            result = work_fn(facade)
            self._enqueue(self._fmt(server, f"{self.ICONS['done']} DONE", color=self._color(server)))
            self._write_log(server, "DONE")
            return result
        except Exception as exc:  # pylint: disable=broad-except
            msg = f"{self.ICONS['fail']} FAILED: {exc}"
            self._enqueue(self._fmt(server, msg, color=self._color(server)))
            self._write_log(server, msg)
            raise

    def _log_consumer(self) -> None:
        """Print logs from the queue with ordering."""
        while not self._stop_event.is_set() or not self._log_queue.empty():
            try:
                line = self._log_queue.get(timeout=0.2)
                print(line, flush=True)
            except queue.Empty:
                continue

    def _enqueue(self, message: str) -> None:
        """Enqueue a log line."""
        self._log_queue.put(message)

    def _fmt(self, server: str, msg: str, color: Optional[str] = None) -> str:
        """Prefix log lines with server and timestamp."""
        ts = time.strftime("%H:%M:%S")
        color_prefix = color or ""
        color_suffix = self.RESET if color else ""
        return f"{color_prefix}[{ts}][{server}] {msg}{color_suffix}"

    def _color(self, server: str) -> str:
        """Assign a deterministic color per server."""
        if server not in self._color_map:
            self._color_map[server] = self.COLORS[len(self._color_map) % len(self.COLORS)]
        return self._color_map[server]

    def _write_log(self, server: str, message: str) -> None:
        """Write per-server log file if enabled."""
        if not self._log_dir:
            return
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        path = self._log_dir / f"{server}.log"
        try:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(f"[{ts}] {message}\n")
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug("Failed to write log for %s: %s", server, exc)
