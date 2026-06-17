"""Watchdog-based file system watcher for auto-indexing."""

from __future__ import annotations

from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from raven.config import DATA_DIR, INDEXED_EXTENSIONS, WATCH_PATHS
from raven.logging_config import get_logger
from raven.rag.indexer import FileIndexer, is_excluded

logger = get_logger("raven.watcher")

_DATA_DIR = str(Path(DATA_DIR).resolve())


class _Handler(FileSystemEventHandler):
    def __init__(self, indexer: FileIndexer):
        self._indexer = indexer

    def _relevant(self, path: str | bytes) -> bool:
        p = Path(str(path)).resolve()
        # Never (re)index our own data dir — index_state.json / chroma files
        # would otherwise trigger an infinite write→event→index feedback loop.
        if str(p) == _DATA_DIR or str(p).startswith(_DATA_DIR + "/"):
            return False
        # Skip hidden/dot dirs (.claude, .config, .git, ...) and heavy/junk dirs —
        # these churn with app state, not documents.
        if is_excluded(p):
            return False
        return p.suffix.lower() in INDEXED_EXTENSIONS

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._relevant(event.src_path):
            logger.info("file_event", type="created", path=str(event.src_path))
            self._indexer.index_file(Path(str(event.src_path)))

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._relevant(event.src_path):
            logger.info("file_event", type="modified", path=str(event.src_path))
            self._indexer.index_file(Path(str(event.src_path)))

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._relevant(event.src_path):
            logger.info("file_event", type="deleted", path=str(event.src_path))
            self._indexer.remove_file(str(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            if self._relevant(event.src_path):
                self._indexer.remove_file(str(event.src_path))
            if self._relevant(event.dest_path):
                self._indexer.index_file(Path(str(event.dest_path)))


class FileWatcher:
    def __init__(self, indexer: FileIndexer | None = None, paths: list[str] | None = None):
        self._indexer = indexer or FileIndexer()
        self._paths = paths or WATCH_PATHS
        self._observer = Observer()

    def start(self) -> None:
        handler = _Handler(self._indexer)
        scheduled = 0
        for path in self._paths:
            p = Path(path)
            if not p.exists():
                logger.warning("watcher_path_missing", path=str(p))
                continue
            # inotify is unsupported on Windows drvfs/9p mounts (/mnt/*): a recursive
            # schedule walks the entire tree (very slow) and never delivers events.
            # Those paths must be (re)indexed on demand or via a scheduled job instead.
            if str(p).startswith("/mnt/"):
                logger.warning(
                    "watcher_path_skipped",
                    path=str(p),
                    reason="inotify unsupported on /mnt mounts; use /index or a timer",
                )
                continue
            self._observer.schedule(handler, str(p), recursive=True)
            logger.info("watcher_started", path=str(p))
            scheduled += 1
        if scheduled:
            self._observer.start()
        else:
            logger.warning("watcher_idle", reason="no inotify-capable paths scheduled")

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()
