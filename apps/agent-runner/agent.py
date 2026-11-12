"""The repo-analyst agent: a LangGraph loop of model and tool steps."""

import os
from typing import Annotated, Literal, TypedDict

import perturvia
from langchain_core.messages import AIMessage, AnyMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph

MODEL_NAME = os.getenv("PERTURVIA_MODEL", "qwen3.5:9b")
TEMPERATURE = 0


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_agent(tools: list[BaseTool]) -> CompiledStateGraph:
    """Build the model -> tools -> model loop around the given tools."""
    model = ChatOllama(model=MODEL_NAME, temperature=TEMPERATURE).bind_tools(tools)
    tools_by_name = {tool.name: tool for tool in tools}

    async def call_model(state: AgentState) -> dict:
        with perturvia.span(MODEL_NAME, kind="llm") as span:
            span.set_attribute("llm.model", MODEL_NAME)
            response = await model.ainvoke(state["messages"])
            usage = response.usage_metadata
            if usage:
                span.set_attribute("llm.input_tokens", usage["input_tokens"])
                span.set_attribute("llm.output_tokens", usage["output_tokens"])
        return {"messages": [response]}

    async def call_tools(state: AgentState) -> dict:
        # Sequential on purpose: a fixed order keeps span sequences repeatable across runs.
        last = state["messages"][-1]
        assert isinstance(last, AIMessage)
        results: list[ToolMessage] = []
        for call in last.tool_calls:
            tool = tools_by_name.get(call["name"])
            if tool is None:
                content = f"Error: Unknown tool {call['name']!r}."
                status = "error"
            else:
                try:
                    content = await tool.ainvoke(call["args"])
                    status = "error" if content.startswith("Error:") else "success"
                except Exception as exc:
                    content = f"Error: {type(exc).__name__}: {exc}"
                    status = "error"
            results.append(
                ToolMessage(
                    content=content, tool_call_id=call["id"], name=call["name"], status=status
                )
            )
        return {"messages": results}

    def route_after_model(state: AgentState) -> Literal["tools", "__end__"]:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("model", call_model)
    graph.add_node("tools", call_tools)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", route_after_model)
    graph.add_edge("tools", "model")
    return graph.compile()
