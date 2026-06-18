"""Shared helper for the desktop shells: locate or start the Raven API server.

Strategy (``ensure_server``):
1. If ``RAVEN_URL`` is set, use it as-is (point at a remote/WSL daemon).
2. Else if a daemon already answers on the local port, reuse it (thin shell).
3. Else start an embedded uvicorn server in a background thread (all-in-one).

The thin-shell path is what keeps a packaged ``.exe`` small: the heavy AI stack
(langchain, qdrant-client, ...) stays in the long-running daemon, not in the GUI binary.
"""

from __future__ import annotations

import os
import threading
import time
import urllib.request

from raven.config import PORT


def _is_up(port: int, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def _wait_up(port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_up(port, timeout=1.0):
            return True
        time.sleep(0.3)
    return False


def _start_embedded(port: int) -> None:
    """Run uvicorn in a daemon thread (signal handlers skipped: not main thread)."""
    import uvicorn

    config = uvicorn.Config("raven.api.app:app", host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None  # type: ignore[method-assign]
    threading.Thread(target=server.run, daemon=True).start()


def ensure_server() -> str:
    """Return a base URL the desktop window can load, starting a server if needed."""
    remote = os.getenv("RAVEN_URL")
    if remote:
        return remote.rstrip("/")

    port = PORT
    if _is_up(port):
        return f"http://127.0.0.1:{port}"

    _start_embedded(port)
    if not _wait_up(port, timeout=30.0):
        raise RuntimeError(f"Embedded Raven server did not come up on port {port}")
    return f"http://127.0.0.1:{port}"
