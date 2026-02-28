"""
metricon_client.py — Standalone Metricon client library.

Usage:
    pip install requests psutil

    # First-time registration
    client = MetriconClient.register(server_url="http://localhost:8000", name="my-bot")
    print(client.api_key)   # save this

    # Normal usage
    client = MetriconClient(
        server_url="http://localhost:8000",
        api_key="<your-key>",
        bot_name="my-bot",   # optional, for logging only
    )
    client.start()

    @client.track
    def handle_command(cmd):
        ...

    @client.track
    async def handle_async(update):
        ...

    client.track_request("/buy", 45, "user123", success=True)
    client.track_error(exc, command="/buy")
    client.track_metric("queue_depth", 17)

    client.stop()
"""
from __future__ import annotations

import asyncio
import functools
import hashlib
import inspect
import logging
import threading
import time
import traceback
from typing import Any, Callable, Optional

log = logging.getLogger("metricon_client")

# ---------------------------------------------------------------------------
# Optional dependencies
# ---------------------------------------------------------------------------
try:
    import requests as _requests
except ImportError:
    _requests = None  # type: ignore

try:
    import psutil as _psutil
except ImportError:
    _psutil = None  # type: ignore


# ---------------------------------------------------------------------------
# MetriconClient
# ---------------------------------------------------------------------------

class MetriconClient:
    """Thread-safe, non-blocking Metricon metrics client.

    All network I/O runs in daemon threads — no call ever blocks the bot.
    """

    HEARTBEAT_INTERVAL = 30   # seconds
    BATCH_INTERVAL = 5        # seconds
    MAX_BATCH_SIZE = 50       # force-flush threshold

    def __init__(
        self,
        server_url: str,
        api_key: str,
        bot_name: str = "unnamed-bot",
        timeout: int = 5,
    ):
        if _requests is None:
            raise ImportError("Install 'requests': pip install requests")

        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.bot_name = bot_name
        self.timeout = timeout

        self._lock = threading.Lock()
        self._batch: list[dict] = []
        self._running = False
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._flush_thread: Optional[threading.Thread] = None
        self._process = _psutil.Process() if _psutil else None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> "MetriconClient":
        """Start background heartbeat + batch-flush threads. Returns self."""
        if self._running:
            return self
        self._running = True

        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, name="metricon-heartbeat", daemon=True
        )
        self._flush_thread = threading.Thread(
            target=self._flush_loop, name="metricon-flush", daemon=True
        )
        self._heartbeat_thread.start()
        self._flush_thread.start()
        log.info("MetriconClient started for bot=%s", self.bot_name)
        return self

    def stop(self) -> None:
        """Gracefully stop: flush remaining batch, then shut down threads."""
        self._running = False
        self._flush_batch()
        log.info("MetriconClient stopped for bot=%s", self.bot_name)

    # ------------------------------------------------------------------
    # Tracking API
    # ------------------------------------------------------------------

    def track(self, fn: Callable) -> Callable:
        """Decorator — works on both sync and async functions.

        Records command name (function name), response time, and success/error.
        ``user_id`` is read from the first argument named ``user_id`` or
        from ``update.effective_user.id`` (python-telegram-bot style) if present.
        Falls back to "anonymous".
        """
        command = f"/{fn.__name__}"

        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                user_id = _extract_user_id(args, kwargs)
                t0 = time.monotonic()
                try:
                    result = await fn(*args, **kwargs)
                    ms = int((time.monotonic() - t0) * 1000)
                    self.track_request(command, ms, user_id, success=True)
                    return result
                except Exception as exc:
                    ms = int((time.monotonic() - t0) * 1000)
                    self.track_request(command, ms, user_id, success=False)
                    self.track_error(exc, command=command)
                    raise
            return async_wrapper
        else:
            @functools.wraps(fn)
            def sync_wrapper(*args, **kwargs):
                user_id = _extract_user_id(args, kwargs)
                t0 = time.monotonic()
                try:
                    result = fn(*args, **kwargs)
                    ms = int((time.monotonic() - t0) * 1000)
                    self.track_request(command, ms, user_id, success=True)
                    return result
                except Exception as exc:
                    ms = int((time.monotonic() - t0) * 1000)
                    self.track_request(command, ms, user_id, success=False)
                    self.track_error(exc, command=command)
                    raise
            return sync_wrapper

    def track_request(
        self,
        command: str,
        response_time_ms: int,
        user_id: str = "anonymous",
        success: bool = True,
    ) -> None:
        """Add a request log to the pending batch."""
        entry = {
            "command": command,
            "user_id": str(user_id),
            "response_time_ms": max(0, int(response_time_ms)),
            "success": bool(success),
        }
        with self._lock:
            self._batch.append(entry)
            should_flush = len(self._batch) >= self.MAX_BATCH_SIZE

        if should_flush:
            threading.Thread(
                target=self._flush_batch, name="metricon-flush-force", daemon=True
            ).start()

    def track_error(self, exc: Exception, command: str = "") -> None:
        """Fire-and-forget error event."""
        payload = {
            "error_type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
            "command": command,
        }
        threading.Thread(
            target=self._post, args=("/api/v1/metrics/error/", payload),
            name="metricon-error", daemon=True
        ).start()

    def track_metric(self, key: str, value: float) -> None:
        """Fire-and-forget custom metric."""
        payload = {"key": key, "value": float(value)}
        threading.Thread(
            target=self._post, args=("/api/v1/metrics/custom/", payload),
            name="metricon-custom", daemon=True
        ).start()

    # ------------------------------------------------------------------
    # Class method: first-time registration
    # ------------------------------------------------------------------

    @classmethod
    def register(
        cls,
        server_url: str,
        name: str,
        description: str = "",
        **kwargs,
    ) -> "MetriconClient":
        """Register a new bot and return a configured client.

        >>> client = MetriconClient.register("http://localhost:8000", "my-bot")
        >>> print(client.api_key)   # save this!
        """
        if _requests is None:
            raise ImportError("Install 'requests': pip install requests")

        url = server_url.rstrip("/") + "/api/v1/bots/register/"
        resp = _requests.post(
            url,
            json={"name": name, "description": description},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        api_key = data["api_key"]
        print(f"[Metricon] Registered bot '{name}' — api_key={api_key}")
        return cls(server_url=server_url, api_key=api_key, bot_name=name, **kwargs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict:
        return {"X-API-Key": self.api_key, "Content-Type": "application/json"}

    def _post(self, path: str, payload: Any) -> None:
        try:
            _requests.post(
                self.server_url + path,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except Exception as exc:
            log.debug("Metricon POST %s failed: %s", path, exc)

    def _flush_batch(self) -> None:
        with self._lock:
            if not self._batch:
                return
            batch = self._batch[:]
            self._batch.clear()

        self._post("/api/v1/metrics/request/batch/", {"logs": batch})

    def _heartbeat_loop(self) -> None:
        while self._running:
            self._send_heartbeat()
            time.sleep(self.HEARTBEAT_INTERVAL)

    def _flush_loop(self) -> None:
        while self._running:
            time.sleep(self.BATCH_INTERVAL)
            self._flush_batch()

    def _send_heartbeat(self) -> None:
        cpu = 0.0
        memory_mb = 0.0
        connections = 0

        if _psutil and self._process:
            try:
                cpu = _psutil.cpu_percent(interval=None)
                memory_mb = self._process.memory_info().rss / (1024 * 1024)
                connections = len(self._process.net_connections())
            except Exception:
                pass

        uptime = int(time.time() - (_psutil.boot_time() if _psutil else time.time()))

        payload = {
            "uptime_seconds": uptime,
            "cpu_percent": round(cpu, 2),
            "memory_mb": round(memory_mb, 2),
            "active_connections": connections,
        }
        self._post("/api/v1/bots/heartbeat/", payload)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_user_id(args: tuple, kwargs: dict) -> str:
    """Try to extract a user_id from function arguments."""
    # Keyword argument
    if "user_id" in kwargs:
        return str(kwargs["user_id"])

    # python-telegram-bot: update.effective_user.id
    for arg in args:
        try:
            return str(arg.effective_user.id)
        except AttributeError:
            pass

    # First positional string argument (heuristic)
    for arg in args:
        if isinstance(arg, str) and arg:
            return arg

    return "anonymous"


# ---------------------------------------------------------------------------
# Quick smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    server = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    key = sys.argv[2] if len(sys.argv) > 2 else None

    if key is None:
        print("Usage: python metricon_client.py <server_url> <api_key>")
        print("  or for registration: python metricon_client.py <server_url> register <name>")
        sys.exit(1)

    if key == "register":
        name = sys.argv[3] if len(sys.argv) > 3 else "test-bot"
        c = MetriconClient.register(server, name)
        print(f"api_key={c.api_key}")
        sys.exit(0)

    c = MetriconClient(server, key, bot_name="test-bot")
    c.start()

    print("Sending test data...")
    c.track_request("/test", 42, "user1", success=True)
    c.track_request("/test", 120, "user2", success=True)
    c.track_request("/fail", 5, "user3", success=False)
    c.track_metric("queue_depth", 7)

    try:
        raise ValueError("test error for Metricon")
    except ValueError as e:
        c.track_error(e, command="/fail")

    print("Waiting for batch flush...")
    time.sleep(7)
    c.stop()
    print("Done.")
