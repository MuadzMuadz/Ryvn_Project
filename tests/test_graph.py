"""Tests for raven.graph.nodes — routing logic."""

from types import SimpleNamespace


def test_should_continue_with_tool_calls():
    from raven.graph.nodes import should_continue

    msg = SimpleNamespace(tool_calls=[{"name": "search"}])
    state = {"messages": [msg]}
    assert should_continue(state) == "tools"


def test_should_continue_end():
    from raven.graph.nodes import should_continue

    msg = SimpleNamespace(tool_calls=[])
    state = {"messages": [msg]}
    assert should_continue(state) == "end"


def test_should_continue_no_attr():
    """Message without tool_calls attribute should end."""
    from raven.graph.nodes import should_continue

    msg = SimpleNamespace()
    state = {"messages": [msg]}
    assert should_continue(state) == "end"
