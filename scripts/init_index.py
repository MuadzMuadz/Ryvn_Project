"""One-shot script to do initial indexing of configured WATCH_PATHS."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from raven.config import WATCH_PATHS, INDEXED_EXTENSIONS
from raven.rag.indexer import FileIndexer
from rich.console import Console
from rich.progress import track

console = Console()


def main():
    indexer = FileIndexer()
    console.print(f"[bold]Raven Init Indexer[/bold]")
    console.print(f"Watching paths: {WATCH_PATHS}")
    console.print(f"Extensions: {INDEXED_EXTENSIONS}\n")

    total = 0
    for path in WATCH_PATHS:
        from pathlib import Path
        p = Path(path)
        if not p.exists():
            console.print(f"[yellow]Skipping (not found):[/yellow] {p}")
            continue
        console.print(f"[cyan]Indexing:[/cyan] {p} ...")
        n = indexer.index_directory(p)
        total += n
        console.print(f"  → {n} chunks")

    console.print(f"\n[green]Done.[/green] Total chunks indexed: {total}")
    console.print(f"Vector store size: {indexer.store.count()} chunks")


if __name__ == "__main__":
    main()
