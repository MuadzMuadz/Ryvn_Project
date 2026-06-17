"""Raven desktop — Option A: pywebview.

Ultralight native window wrapping the local web UI. Uses the OS webview
(WebView2 on Windows, WebKit on Linux/macOS), so the binary stays small.

Run:    uv run python -m raven.desktop.pywebview_app
Install: uv sync --extra desktop-webview     (or: pip install "raven[desktop-webview]")
"""

from __future__ import annotations

from raven.desktop._server import ensure_server


def main() -> None:
    import webview

    url = ensure_server()
    webview.create_window(
        "Raven · Thought & Memory",
        url,
        width=1120,
        height=800,
        min_size=(720, 560),
        background_color="#0a0a0c",
    )
    webview.start()


if __name__ == "__main__":
    main()
