from agents.retail_analytics.schemas import RequestCategory
from agents.retail_analytics.state import RetailAgentState


def route_after_classification(state: RetailAgentState) -> RequestCategory:
    return state.category or RequestCategory.ANALYTICS
