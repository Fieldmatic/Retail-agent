from enum import StrEnum

from agents.retail_analytics.schemas import QueryStage
from agents.retail_analytics.state import RetailAgentState

MAX_ATTEMPTS = 3


class QueryExecutionRoute(StrEnum):
    EXECUTE = "execute"
    RETRY = "retry"
    FAIL = "fail"
    REPORT = "report"


def route_after_validation(state: RetailAgentState) -> QueryExecutionRoute:
    if not state.error:
        return QueryExecutionRoute.EXECUTE
    if state.attempts < MAX_ATTEMPTS:
        return QueryExecutionRoute.RETRY
    return QueryExecutionRoute.FAIL


def route_after_query_execution(state: RetailAgentState) -> QueryExecutionRoute:
    if not state.error:
        return QueryExecutionRoute.REPORT
    if state.error.stage == QueryStage.EMPTY:
        if state.attempts < MAX_ATTEMPTS:
            return QueryExecutionRoute.RETRY
        return QueryExecutionRoute.REPORT
    if state.attempts < MAX_ATTEMPTS:
        return QueryExecutionRoute.RETRY
    return QueryExecutionRoute.FAIL
