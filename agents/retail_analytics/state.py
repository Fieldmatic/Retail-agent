from typing import TypedDict

from pydantic import BaseModel, ConfigDict

from agents.retail_analytics.schemas import QueryError, QueryResult, SqlPlan


class RetailAgentState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    attempts: int = 0
    sql_plan: SqlPlan | None = None
    validated_sql: str | None = None
    query_result: QueryResult | None = None
    error: QueryError | None = None
    answer: str | None = None


class SqlPlannerUpdate(TypedDict):
    sql_plan: SqlPlan
    attempts: int
    error: None


class ValidationUpdate(TypedDict, total=False):
    validated_sql: str
    error: QueryError | None


class QueryUpdate(TypedDict, total=False):
    query_result: QueryResult
    error: QueryError | None


class AnswerUpdate(TypedDict):
    answer: str
