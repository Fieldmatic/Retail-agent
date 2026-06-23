from langgraph.graph import END, START, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel

from agents.retail_analytics.nodes import build_analytics_agent_node
from agents.retail_analytics.state import RetailAgentState


def build_graph(llm: BaseChatModel):
    graph = StateGraph(RetailAgentState)
    graph.add_node("analytics_agent", build_analytics_agent_node(llm))
    graph.add_edge(START, "analytics_agent")
    graph.add_edge("analytics_agent", END)
    return graph.compile()
