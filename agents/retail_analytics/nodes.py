from collections.abc import Callable
from typing import Any, cast

from langchain.agents import create_agent  # pyright: ignore[reportUnknownVariableType]
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError

from agents.retail_analytics.messages import REQUEST_FAILED_MESSAGE
from agents.retail_analytics.prompts import (
    ANALYST_SYSTEM_PROMPT,
    CLASSIFIER_SYSTEM_PROMPT,
    REFUSAL_MESSAGE,
)
from agents.retail_analytics.schemas import RequestClassification
from agents.retail_analytics.services.bigquery_client import BigQueryClient
from agents.retail_analytics.state import AnswerUpdate, ClassificationUpdate, RetailAgentState
from agents.retail_analytics.tools import build_tools

RECURSION_LIMIT = 10
CLI_THREAD_ID = "cli-session"


def build_classifier_node(
    llm: BaseChatModel,
) -> Callable[[RetailAgentState], ClassificationUpdate]:
    classifier = llm.with_structured_output(RequestClassification)

    def node(state: RetailAgentState) -> ClassificationUpdate:
        result = cast(
            RequestClassification,
            classifier.invoke([("system", CLASSIFIER_SYSTEM_PROMPT), ("human", state.question)]),
        )
        return {"category": result.category}

    return node


def _message_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(
        str(block["text"])
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def build_agent_node(
    llm: BaseChatModel,
    bigquery_client: BigQueryClient,
) -> Callable[[RetailAgentState], AnswerUpdate]:
    agent = cast(
        Any,
        create_agent(
            llm,
            build_tools(bigquery_client),
            system_prompt=ANALYST_SYSTEM_PROMPT,
            checkpointer=InMemorySaver(),
        ),
    )

    def node(state: RetailAgentState) -> AnswerUpdate:
        try:
            result = agent.invoke(
                {"messages": [HumanMessage(content=state.question)]},
                {"recursion_limit": RECURSION_LIMIT, "configurable": {"thread_id": CLI_THREAD_ID}},
            )
        except GraphRecursionError:
            return {"answer": REQUEST_FAILED_MESSAGE}
        messages = cast(list[Any], result["messages"])
        answer = _message_text(messages[-1]) if messages else ""
        return {"answer": answer or "I couldn't produce an answer."}

    return node


def refuse_node(state: RetailAgentState) -> AnswerUpdate:
    return {"answer": REFUSAL_MESSAGE}
