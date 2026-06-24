from enum import StrEnum

from agents.retail_analytics.state import RetailAgentState

MAX_ATTEMPTS = 2


class QueryExecutionRoute(StrEnum):
    RETRY = "retry"
    FAIL = "fail"
    REPORT = "report"


def route_after_query_execution(state: RetailAgentState) -> QueryExecutionRoute:
    if state.error and state.attempts < MAX_ATTEMPTS:
        return QueryExecutionRoute.RETRY
    if state.error:
        return QueryExecutionRoute.FAIL
    return QueryExecutionRoute.REPORT
