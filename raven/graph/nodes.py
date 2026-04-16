"""LangGraph nodes."""
from __future__ import annotations

from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI

from raven.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from raven.graph.state import AgentState
from raven.graph.tools import TOOLS, TOOLS_BY_NAME
from raven.rag.vectorstore import get_store

_store = get_store()

SYSTEM_PROMPT = """You are Raven, a highly capable personal AI assistant with access to the user's local file system and the web.

You can:
- Search and retrieve information from local documents indexed from the user's file system
- Scrape and crawl web pages via Firecrawl
- Search the web for current information
- Index new files or URLs on demand

Always cite your sources. Be concise and direct. When you retrieve context from local docs, mention the filename."""


def _llm():
    kwargs = dict(model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0)
    if OPENAI_BASE_URL:
        kwargs["base_url"] = OPENAI_BASE_URL
    return ChatOpenAI(**kwargs).bind_tools(TOOLS)


def retrieve_node(state: AgentState) -> dict:
    """Retrieve relevant docs from the vector store based on last user message."""
    last_human = next(
        (m for m in reversed(state["messages"]) if m.type == "human"), None
    )
    if last_human is None:
        return {"retrieved_docs": []}

    docs = _store.query(last_human.content, n_results=5)
    return {"retrieved_docs": docs}


def agent_node(state: AgentState) -> dict:
    """LLM reasoning node."""
    docs = state.get("retrieved_docs", [])
    context = ""
    if docs:
        context = "\n\n## Retrieved Context\n" + "\n---\n".join(
            f"**[{d['metadata'].get('filename', 'unknown')}]** (score: {d['score']:.2f})\n{d['text']}"
            for d in docs
        )

    messages = [SystemMessage(content=SYSTEM_PROMPT + context)] + state["messages"]
    llm = _llm()
    response = llm.invoke(messages)
    return {"messages": [response]}


def tool_node(state: AgentState) -> dict:
    """Execute tool calls from the last AI message."""
    last_ai: AIMessage = state["messages"][-1]
    results = []
    for call in last_ai.tool_calls:
        tool = TOOLS_BY_NAME.get(call["name"])
        if tool is None:
            content = f"Tool '{call['name']}' not found."
        else:
            try:
                content = tool.invoke(call["args"])
            except Exception as e:
                content = f"Error: {e}"
        results.append(ToolMessage(content=str(content), tool_call_id=call["id"]))
    return {"messages": results}


def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "end"
