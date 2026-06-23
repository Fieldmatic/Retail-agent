from collections.abc import Callable

from langchain_core.language_models.chat_models import BaseChatModel

from agents.retail_analytics.prompts import SYSTEM_PROMPT
from agents.retail_analytics.state import RetailAgentState


def build_analytics_agent_node(llm: BaseChatModel) -> Callable[[RetailAgentState], dict[str, str]]:
    def node(state: RetailAgentState) -> dict[str, str]:
        response = llm.invoke(
            [
                ("system", SYSTEM_PROMPT),
                ("human", state.question),
            ]
        )
        return {"answer": str(response.content)}

    return node
