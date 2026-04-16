"""Raven CLI — personal AI assistant."""
from __future__ import annotations

import logging
import threading

from langchain_core.messages import HumanMessage
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt

from raven.graph.agent import get_graph

logging.basicConfig(level=logging.WARNING)
console = Console()


def _start_watcher():
    from raven.config import WATCH_PATHS
    from raven.rag.watcher import FileWatcher
    from raven.rag.indexer import FileIndexer
    indexer = FileIndexer()
    watcher = FileWatcher(indexer=indexer, paths=WATCH_PATHS)
    watcher.start()
    return watcher


def chat():
    console.print("[bold cyan]Raven[/bold cyan] — Personal AI Assistant")
    console.print("Type [bold]/exit[/bold] to quit, [bold]/index <path>[/bold] to index a file/dir\n")

    # Start file watcher in background
    watcher_thread = threading.Thread(target=_start_watcher, daemon=True)
    watcher_thread.start()

    graph = get_graph()
    state: dict = {"messages": [], "retrieved_docs": [], "tool_calls": [], "metadata": {}}

    while True:
        try:
            user_input = Prompt.ask("[bold green]You[/bold green]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not user_input.strip():
            continue

        if user_input.strip() == "/exit":
            console.print("[dim]Goodbye.[/dim]")
            break

        if user_input.strip().startswith("/index "):
            path = user_input.strip()[7:].strip()
            from raven.rag.indexer import FileIndexer
            indexer = FileIndexer()
            from pathlib import Path
            p = Path(path)
            if p.is_file():
                n = indexer.index_file(p)
            else:
                n = indexer.index_directory(p)
            console.print(f"[dim]Indexed {n} chunks.[/dim]")
            continue

        state["messages"].append(HumanMessage(content=user_input))

        with console.status("[dim]Thinking...[/dim]", spinner="dots"):
            state = graph.invoke(state)

        last = state["messages"][-1]
        console.print("\n[bold cyan]Raven:[/bold cyan]")
        console.print(Markdown(last.content))
        console.print()


if __name__ == "__main__":
    chat()
