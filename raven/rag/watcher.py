"""Watchdog-based file system watcher for auto-indexing."""
from __future__ import annotations

import logging
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from raven.config import WATCH_PATHS, INDEXED_EXTENSIONS
from raven.rag.indexer import FileIndexer

logger = logging.getLogger(__name__)


class _Handler(FileSystemEventHandler):
    def __init__(self, indexer: FileIndexer):
        self._indexer = indexer

    def _relevant(self, path: str) -> bool:
        return Path(path).suffix.lower() in INDEXED_EXTENSIONS

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._relevant(event.src_path):
            logger.info(f"[watcher] indexing new file: {event.src_path}")
            self._indexer.index_file(Path(event.src_path))

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._relevant(event.src_path):
            logger.info(f"[watcher] re-indexing modified: {event.src_path}")
            self._indexer.index_file(Path(event.src_path))

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._relevant(event.src_path):
            logger.info(f"[watcher] removing deleted: {event.src_path}")
            self._indexer.remove_file(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            if self._relevant(event.src_path):
                self._indexer.remove_file(event.src_path)
            if self._relevant(event.dest_path):
                self._indexer.index_file(Path(event.dest_path))


class FileWatcher:
    def __init__(self, indexer: FileIndexer | None = None, paths: list[str] | None = None):
        self._indexer = indexer or FileIndexer()
        self._paths = paths or WATCH_PATHS
        self._observer = Observer()

    def start(self) -> None:
        handler = _Handler(self._indexer)
        for path in self._paths:
            p = Path(path)
            if p.exists():
                self._observer.schedule(handler, str(p), recursive=True)
                logger.info(f"[watcher] watching: {p}")
            else:
                logger.warning(f"[watcher] path not found, skipping: {p}")
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()
