from collections.abc import Iterator
from typing import Any, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessageChunk
from langgraph.graph import END, START, StateGraph  # pyright: ignore[reportMissingTypeStubs]

from agents.retail_analytics.nodes import (
    build_classifier_node,
    build_query_node,
    build_report_node,
    build_sql_planner_node,
    mask_pii_node,
    refuse_node,
    safe_failure_node,
    validate_sql_node,
)
from agents.retail_analytics.prompts import build_sql_system_prompt
from agents.retail_analytics.routes import (
    QueryExecutionRoute,
    route_after_classification,
    route_after_query_execution,
    route_after_validation,
)
from agents.retail_analytics.schemas import RequestCategory
from agents.retail_analytics.services.bigquery_client import BigQueryClient
from agents.retail_analytics.state import RetailAgentState
from agents.retail_analytics.types import AnswerGraph

CLASSIFY_NODE = "classify"
PLAN_NODE = "plan_sql"
VALIDATE_SQL_NODE = "validate_sql"
QUERY_NODE = "query_bigquery"
MASK_NODE = "mask_pii"
REPORT_NODE = "write_report"
REFUSE_NODE = "refuse"
FAILURE_NODE = "safe_failure"


def build_graph(llm: BaseChatModel, bigquery_client: BigQueryClient) -> AnswerGraph:
    schema_context = bigquery_client.schema_context()
    sql_system_prompt = build_sql_system_prompt(schema_context)
    graph = StateGraph(RetailAgentState)
    graph.add_node(CLASSIFY_NODE, build_classifier_node(llm))  # pyright: ignore[reportArgumentType, reportUnknownMemberType]
    graph.add_node(PLAN_NODE, build_sql_planner_node(llm, sql_system_prompt))  # pyright: ignore[reportArgumentType, reportUnknownMemberType]
    graph.add_node(VALIDATE_SQL_NODE, validate_sql_node)  # pyright: ignore[reportArgumentType, reportUnknownMemberType]
    graph.add_node(QUERY_NODE, build_query_node(bigquery_client))  # pyright: ignore[reportArgumentType, reportUnknownMemberType]
    graph.add_node(MASK_NODE, mask_pii_node)  # pyright: ignore[reportArgumentType, reportUnknownMemberType]
    graph.add_node(REPORT_NODE, build_report_node(llm))  # pyright: ignore[reportArgumentType, reportUnknownMemberType]
    graph.add_node(REFUSE_NODE, refuse_node)  # pyright: ignore[reportArgumentType, reportUnknownMemberType]
    graph.add_node(FAILURE_NODE, safe_failure_node)  # pyright: ignore[reportArgumentType, reportUnknownMemberType]

    graph.add_edge(START, CLASSIFY_NODE)
    graph.add_conditional_edges(
        CLASSIFY_NODE,
        route_after_classification,
        {
            RequestCategory.ANALYTICS: PLAN_NODE,
            RequestCategory.OFF_TOPIC: REFUSE_NODE,
        },
    )
    graph.add_edge(PLAN_NODE, VALIDATE_SQL_NODE)
    graph.add_conditional_edges(
        VALIDATE_SQL_NODE,
        route_after_validation,
        {
            QueryExecutionRoute.EXECUTE: QUERY_NODE,
            QueryExecutionRoute.RETRY: PLAN_NODE,
            QueryExecutionRoute.FAIL: FAILURE_NODE,
        },
    )
    graph.add_conditional_edges(
        QUERY_NODE,
        route_after_query_execution,
        {
            QueryExecutionRoute.RETRY: PLAN_NODE,
            QueryExecutionRoute.FAIL: FAILURE_NODE,
            QueryExecutionRoute.REPORT: MASK_NODE,
        },
    )
    graph.add_edge(MASK_NODE, REPORT_NODE)
    graph.add_edge(REPORT_NODE, END)
    graph.add_edge(REFUSE_NODE, END)
    graph.add_edge(FAILURE_NODE, END)

    return cast(AnswerGraph, graph.compile())  # pyright: ignore[reportUnknownMemberType]


def stream_answer(graph: AnswerGraph, question: str) -> Iterator[str]:
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
                if isinstance(update, dict):
                    answer = cast(dict[str, object], update).get("answer")
                    if isinstance(answer, str):
                        final_answer = answer

    if not streamed_report and final_answer:
        yield final_answer
