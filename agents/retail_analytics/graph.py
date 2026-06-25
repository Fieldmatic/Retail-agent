from typing import Protocol, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph  # pyright: ignore[reportMissingTypeStubs]

from agents.retail_analytics.nodes import (
    build_agent_node,
    build_classifier_node,
    refuse_node,
)
from agents.retail_analytics.routes import route_after_classification
from agents.retail_analytics.schemas import RequestCategory
from agents.retail_analytics.services.bigquery_client import BigQueryClient
from agents.retail_analytics.state import RetailAgentState


class AnswerGraph(Protocol):
    def invoke(self, input: dict[str, str]) -> dict[str, object]: ...


CLASSIFY_NODE = "classify"
ANALYST_NODE = "analyst"
REFUSE_NODE = "refuse"


def build_graph(llm: BaseChatModel, bigquery_client: BigQueryClient) -> AnswerGraph:
    graph = StateGraph(RetailAgentState)
    graph.add_node(CLASSIFY_NODE, build_classifier_node(llm))  # pyright: ignore[reportArgumentType, reportUnknownMemberType]
    graph.add_node(ANALYST_NODE, build_agent_node(llm, bigquery_client))  # pyright: ignore[reportArgumentType, reportUnknownMemberType]
    graph.add_node(REFUSE_NODE, refuse_node)  # pyright: ignore[reportUnknownMemberType]

    graph.add_edge(START, CLASSIFY_NODE)
    graph.add_conditional_edges(
        CLASSIFY_NODE,
        route_after_classification,
        {
            RequestCategory.ANALYTICS: ANALYST_NODE,
            RequestCategory.OFF_TOPIC: REFUSE_NODE,
        },
    )
    graph.add_edge(ANALYST_NODE, END)
    graph.add_edge(REFUSE_NODE, END)

    return cast(AnswerGraph, graph.compile())  # pyright: ignore[reportUnknownMemberType]


def answer_question(graph: AnswerGraph, question: str) -> str:
    result = graph.invoke({"question": question})
    answer = result.get("answer")
    return answer if isinstance(answer, str) else "I couldn't produce an answer."
