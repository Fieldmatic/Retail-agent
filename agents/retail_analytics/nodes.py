from collections.abc import Callable
from typing import cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from agents.retail_analytics.prompts import REPORT_SYSTEM_PROMPT
from agents.retail_analytics.schemas import (
    QueryError,
    SqlPlan,
)
from agents.retail_analytics.state import (
    AnswerUpdate,
    QueryUpdate,
    RetailAgentState,
    SqlPlannerUpdate,
)
from agents.retail_analytics.tools.bigquery_client import BigQueryClient


def build_sql_planner_node(
    llm: BaseChatModel,
    sql_system_prompt: str,
) -> Callable[[RetailAgentState], SqlPlannerUpdate]:
    planner = llm.with_structured_output(SqlPlan)

    def node(state: RetailAgentState) -> SqlPlannerUpdate:
        feedback = ""
        if state.error:
            feedback = (
                f"\n\nAttempt {state.attempts} failed at {state.error.stage}.\n\n"
                f"Reason:\n{state.error.message}\n\n"
                "Revise the SQL and try again."
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


def build_query_node(
    validate_sql_tool: BaseTool,
    bigquery_client: BigQueryClient,
) -> Callable[[RetailAgentState], QueryUpdate]:
    def node(state: RetailAgentState) -> QueryUpdate:
        if state.sql_plan is None:
            return {"error": QueryError(stage="planning", message="No SQL plan was generated.")}

        validation = validate_sql_tool.invoke({"sql": state.sql_plan.sql})
        if not validation.valid or validation.sql is None:
            return {
                "error": QueryError(
                    stage="validation",
                    message=validation.error or "Generated SQL was rejected.",
                )
            }

        try:
            result = bigquery_client.query(validation.sql)
        except Exception as error:
            return {"error": QueryError(stage="bigquery", message=str(error))}

        return {"query_result": result, "error": None}

    return node


def build_report_node(llm: BaseChatModel) -> Callable[[RetailAgentState], AnswerUpdate]:
    def node(state: RetailAgentState) -> AnswerUpdate:
        if state.query_result is None:
            return {"answer": "I could not produce a report because the query did not return data."}

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


def safe_failure_node(state: RetailAgentState) -> AnswerUpdate:
    if state.error:
        return {
            "answer": (
                f"I couldn't answer that safely after {state.attempts} attempts.\n\n"
                f"Last failure:\n{state.error.stage}: {state.error.message}"
            )
        }
    return {"answer": "I couldn't answer that safely."}
