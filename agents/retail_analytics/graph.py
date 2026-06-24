# pyright: reportMissingTypeStubs=false, reportMissingTypeArgument=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownVariableType=false
# -- langgraph/langchain ship no type stubs
from collections.abc import Iterator
from typing import Any, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessageChunk
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.retail_analytics.nodes import (
    build_query_node,
    build_report_node,
    build_sql_planner_node,
    safe_failure_node,
)
from agents.retail_analytics.prompts import build_sql_system_prompt
from agents.retail_analytics.routes import QueryExecutionRoute, route_after_query_execution
from agents.retail_analytics.state import RetailAgentState
from agents.retail_analytics.tools.bigquery_client import BigQueryClient
from agents.retail_analytics.tools.sql_validator import validate_sql_tool

PLAN_NODE = "plan_sql"
QUERY_NODE = "query_bigquery"
REPORT_NODE = "write_report"
FAILURE_NODE = "safe_failure"


def build_graph(llm: BaseChatModel, bigquery_client: BigQueryClient) -> CompiledStateGraph:
    sql_system_prompt = build_sql_system_prompt(bigquery_client.schema_context())
    graph = StateGraph(RetailAgentState)
    # langgraph's add_node overloads reject single-arg node fns as position-only; valid at runtime.
    graph.add_node(PLAN_NODE, build_sql_planner_node(llm, sql_system_prompt))  # pyright: ignore[reportArgumentType]
    graph.add_node(QUERY_NODE, build_query_node(validate_sql_tool, bigquery_client))  # pyright: ignore[reportArgumentType]
    graph.add_node(REPORT_NODE, build_report_node(llm))  # pyright: ignore[reportArgumentType]
    graph.add_node(FAILURE_NODE, safe_failure_node)  # pyright: ignore[reportArgumentType]

    graph.add_edge(START, PLAN_NODE)
    graph.add_edge(PLAN_NODE, QUERY_NODE)
    graph.add_conditional_edges(
        QUERY_NODE,
        route_after_query_execution,
        {
            QueryExecutionRoute.RETRY: PLAN_NODE,
            QueryExecutionRoute.FAIL: FAILURE_NODE,
            QueryExecutionRoute.REPORT: REPORT_NODE,
        },
    )
    graph.add_edge(REPORT_NODE, END)
    graph.add_edge(FAILURE_NODE, END)

    return graph.compile()


def stream_answer(graph: CompiledStateGraph, question: str) -> Iterator[str]:
    streamed_report = False
    final_answer: str | None = None
    for mode, data in graph.stream(
        {"question": question},
        stream_mode=["messages", "updates"],
    ):
        if mode == "messages":
            message_chunk, metadata = cast(tuple[AIMessageChunk, dict[str, Any]], data)
            is_report = metadata.get("langgraph_node") == REPORT_NODE
            if is_report and isinstance(message_chunk.content, str):
                streamed_report = True
                yield message_chunk.content
        else:
            for update in cast(dict[str, Any], data).values():
                if isinstance(update, dict) and update.get("answer"):
                    final_answer = update["answer"]

    if not streamed_report and final_answer:
        yield final_answer
