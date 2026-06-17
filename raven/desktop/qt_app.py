"""Raven desktop — Option B: PySide6 + QWebEngineView.

Renders the same web UI inside a Qt window backed by Chromium (QtWebEngine),
plus a system-tray icon (Show / Quit) so Raven can live in the tray like Jarvis.

Run:    uv run python -m raven.desktop.qt_app
Install: uv sync --extra desktop-qt           (or: pip install "raven[desktop-qt]")
"""

from __future__ import annotations

import sys

from raven.desktop._server import ensure_server


def main() -> None:
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QAction, QGuiApplication, QIcon, QPixmap
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWidgets import QApplication, QMainWindow, QMenu, QSystemTrayIcon

    url = ensure_server()

    app = QApplication(sys.argv)
    app.setApplicationName("Raven")
    app.setApplicationDisplayName("Raven")
    app.setQuitOnLastWindowClosed(False)  # closing the window hides to tray

    win = QMainWindow()
    win.setWindowTitle("Raven · Thought & Memory")
    view = QWebEngineView()
    view.setUrl(QUrl(url))
    win.setCentralWidget(view)
    win.resize(1120, 800)
    win.show()

    # Gilded fallback icon (a solid gold square) if no theme icon is available.
    icon = QIcon.fromTheme("applications-internet")
    if icon.isNull():
        pix = QPixmap(64, 64)
        pix.fill(QGuiApplication.palette().highlight().color())
        icon = QIcon(pix)
    win.setWindowIcon(icon)

    tray = QSystemTrayIcon(icon, parent=win)
    tray.setToolTip("Raven")
    menu = QMenu()
    act_show = QAction("Show Raven", win)
    act_show.triggered.connect(lambda: (win.showNormal(), win.activateWindow()))
    act_quit = QAction("Quit", win)
    act_quit.triggered.connect(app.quit)
    menu.addAction(act_show)
    menu.addSeparator()
    menu.addAction(act_quit)
    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: (win.showNormal(), win.activateWindow())
        if reason == QSystemTrayIcon.ActivationReason.Trigger
        else None
    )
    tray.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
