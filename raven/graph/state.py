"""LangGraph state definition."""
from __future__ import annotations

from typing import Annotated, Any
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    retrieved_docs: list[dict]
    tool_calls: list[dict]
    metadata: dict[str, Any]
