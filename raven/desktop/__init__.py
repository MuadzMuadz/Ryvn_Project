"""Desktop shells for Raven — native windows wrapping the local web UI.

Two interchangeable front-ends, both rendering the same web UI served by FastAPI:
- ``pywebview_app`` — ultralight pywebview window.
- ``qt_app`` — PySide6 + QWebEngineView, with a system-tray icon.

Both connect to an already-running daemon if one is up, otherwise they spin up
an embedded server. See ``raven.desktop._server.ensure_server``.
"""
