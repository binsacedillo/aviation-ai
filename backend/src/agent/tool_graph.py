"""
LangGraph tool-calling agent using LangChain tools.
Supports OpenAI (tool calling) and Ollama (best-effort: if tool_calls unsupported, it will just answer).
"""

from typing import TypedDict, List, Dict, Any
import json
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from config import settings
from ..tools.tools import TOOLS, execute_tool

try:
    from langchain_community.chat_models import ChatOllama
except Exception:  # noqa: BLE001
    ChatOllama = None  # Optional dependency


class GraphState(TypedDict):
    messages: List[Any]


def _build_tools() -> List[Tool]:
    """Wrap registered tools as LangChain Tool objects."""
    wrapped = []
    for name, meta in TOOLS.items():
        def _make_func(tool_name=name):
            def _call(**kwargs):
                return execute_tool(tool_name, **kwargs)
            return _call
        wrapped.append(
            Tool(
                name=name,
                description=meta["description"],
                func=_make_func(),
            )
        )
    return wrapped


def _get_llm():
    """Choose LLM: OpenAI first, then Ollama."""
    if settings.has_openai_key:
        return ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0)
    if settings.has_ollama and ChatOllama is not None:
        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.2,
        )
    raise RuntimeError("No LLM configured for tool-calling (set OPENAI_API_KEY or enable Ollama)")


def build_tool_graph():
    tools = _build_tools()
    llm = _get_llm().bind_tools(tools)

    def call_model(state: GraphState):
        response = llm.invoke(state["messages"])
        return {"messages": state["messages"] + [response]}

    def call_tools(state: GraphState):
        messages = state["messages"]
        last: AIMessage = messages[-1]
        tool_messages: List[ToolMessage] = []
        for tc in getattr(last, "tool_calls", []) or []:
            name = tc.get("name")
            args = tc.get("args", {})
            result = execute_tool(name, **args)
            tool_messages.append(
                ToolMessage(content=json.dumps(result), tool_call_id=tc.get("id", "tool"))
            )
        return {"messages": messages + tool_messages}

    def should_continue(state: GraphState):
        last = state["messages"][-1]
        has_tools = bool(getattr(last, "tool_calls", None))
        return "tools" if has_tools else "end"

    graph = StateGraph(GraphState)
    graph.add_node("model", call_model)
    graph.add_node("tools", call_tools)
    graph.set_entry_point("model")
    graph.add_conditional_edges(
        "model",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )
    graph.add_edge("tools", "model")

    return graph.compile()


def run_tool_agent(user_query: str) -> Dict[str, Any]:
    """Run the LangGraph tool agent once and return final content plus trace."""
    app = build_tool_graph()
    init_state: GraphState = {"messages": [HumanMessage(content=user_query)]}
    result = app.invoke(init_state)
    final_msg = result["messages"][-1]
    return {
        "final_response": getattr(final_msg, "content", ""),
        "messages": result["messages"],
    }


def stream_tool_agent(user_query: str):
    """Stream events from the LangGraph tool agent."""
    app = build_tool_graph()
    init_state: GraphState = {"messages": [HumanMessage(content=user_query)]}
    for event in app.stream(init_state):
        yield event
