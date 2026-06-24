from collections.abc import Callable
from typing import cast

from langchain_core.language_models.chat_models import BaseChatModel

from agents.retail_analytics.prompts import (
    CLASSIFIER_SYSTEM_PROMPT,
    REFUSAL_MESSAGE,
    REPORT_SYSTEM_PROMPT,
)
from agents.retail_analytics.schemas import (
    QueryError,
    QueryResult,
    QueryStage,
    RequestClassification,
    SqlPlan,
)
from agents.retail_analytics.services.bigquery_client import BigQueryClient
from agents.retail_analytics.services.pii_masker import redact_pii
from agents.retail_analytics.services.sql_validator import validate_sql
from agents.retail_analytics.state import (
    AnswerUpdate,
    ClassificationUpdate,
    QueryUpdate,
    RetailAgentState,
    SqlPlannerUpdate,
    ValidationUpdate,
)


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


def refuse_node(state: RetailAgentState) -> AnswerUpdate:
    return {"answer": REFUSAL_MESSAGE}


def build_sql_planner_node(
    llm: BaseChatModel,
    sql_system_prompt: str,
) -> Callable[[RetailAgentState], SqlPlannerUpdate]:
    planner = llm.with_structured_output(SqlPlan)

    def node(state: RetailAgentState) -> SqlPlannerUpdate:
        feedback = ""
        if state.error and state.sql_plan:
            feedback = (
                f"\n\nYour previous SQL failed:\n{state.sql_plan.sql}\n\n"
                f"Error ({state.error.stage}):\n{state.error.message}\n\n"
                "Fix the SQL to resolve this error and try again."
            )
        plan = cast(
            SqlPlan,
            planner.invoke(
                [
                    ("system", sql_system_prompt),
                    ("human", f"Question: {state.question}{feedback}"),
                ]
            ),
        )
        return {"sql_plan": plan, "attempts": state.attempts + 1, "error": None}

    return node


def validate_sql_node(state: RetailAgentState) -> ValidationUpdate:
    if state.sql_plan is None:
        return {
            "error": QueryError(stage=QueryStage.PLANNING, message="No SQL plan was generated.")
        }

    validation = validate_sql(state.sql_plan.sql)
    if not validation.valid or validation.sql is None:
        return {
            "error": QueryError(
                stage=QueryStage.VALIDATION,
                message=validation.error or "Generated SQL was rejected.",
            )
        }

    return {"validated_sql": validation.sql, "error": None}


def build_query_node(
    bigquery_client: BigQueryClient,
) -> Callable[[RetailAgentState], QueryUpdate]:
    def node(state: RetailAgentState) -> QueryUpdate:
        if state.validated_sql is None:
            return {
                "error": QueryError(stage=QueryStage.VALIDATION, message="No validated SQL to run.")
            }

        try:
            result = bigquery_client.query(state.validated_sql)
        except Exception as error:
            return {"error": QueryError(stage=QueryStage.BIGQUERY, message=str(error))}

        if not result.rows:
            return {
                "error": QueryError(
                    stage=QueryStage.EMPTY,
                    message=(
                        "The query returned no rows. The filters or joins may be too "
                        "restrictive, or the data may genuinely not exist."
                    ),
                ),
                "query_result": result,
            }

        return {"query_result": result, "error": None}

    return node


def mask_pii_node(state: RetailAgentState) -> QueryUpdate:
    if state.query_result is None:
        return {}
    return {
        "query_result": QueryResult(
            rows=redact_pii(state.query_result.rows),
            bytes_processed=state.query_result.bytes_processed,
        )
    }


def build_report_node(llm: BaseChatModel) -> Callable[[RetailAgentState], AnswerUpdate]:
    def node(state: RetailAgentState) -> AnswerUpdate:
        if state.query_result is None or not state.query_result.rows:
            return {"answer": "I ran the query but found no matching data for that question."}

        response = llm.invoke(
            [
                ("system", REPORT_SYSTEM_PROMPT),
                (
                    "human",
                    f"Question: {state.question}\n"
                    f"SQL: {state.sql_plan.sql if state.sql_plan else ''}\n"
                    f"Rows: {state.query_result.rows}\n"
                    "Write the report.",
                ),
            ]
        )
        return {"answer": str(response.content)}

    return node


FAILURE_MESSAGES = {
    QueryStage.BIGQUERY: (
        "I ran into a problem running that query. Try rephrasing it or narrowing the time range."
    ),
    QueryStage.VALIDATION: ("I couldn't build a valid query for that question. Try rephrasing it."),
    QueryStage.PLANNING: ("I couldn't build a valid query for that question. Try rephrasing it."),
}


def safe_failure_node(state: RetailAgentState) -> AnswerUpdate:
    if state.error:
        return {"answer": FAILURE_MESSAGES.get(state.error.stage, "I couldn't answer that safely.")}
    return {"answer": "I couldn't answer that safely."}
