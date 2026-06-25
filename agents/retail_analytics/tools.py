from langchain_core.tools import BaseTool, tool

from agents.retail_analytics.services.bigquery_client import BigQueryClient
from agents.retail_analytics.services.pii_masker import redact_pii
from agents.retail_analytics.services.sql_validator import validate_sql


def create_schema_tool(schema_context: str) -> BaseTool:
    @tool
    def get_schema() -> str:
        """Return the available tables and their columns. Call this before writing SQL,
        or to answer questions about the database structure."""
        return schema_context

    return get_schema


def create_query_tool(bigquery_client: BigQueryClient) -> BaseTool:
    @tool
    def run_validated_query(sql: str) -> str:
        """Run a read-only BigQuery SELECT and return the result rows.
        SELECT/WITH only, one statement, no SELECT *; PII is masked automatically.
        On any error this returns an error string — read it, fix the SQL, and call again."""
        validation = validate_sql(sql)

        if not validation.valid or validation.sql is None:
            return f"ERROR (validation): {validation.error or 'SQL was rejected.'}"
        try:
            result = bigquery_client.query(validation.sql)
        except Exception as error:
            return f"ERROR (bigquery): {error}"
        if not result.rows:
            return (
                "NO_ROWS: the query returned nothing. If a filter, join, or time range may be too "
                "narrow, try one broader query; if it is still empty, report no matching data."
            )
        return f"Rows ({len(result.rows)}):\n{redact_pii(result.rows)}"

    return run_validated_query


def build_tools(bigquery_client: BigQueryClient) -> list[BaseTool]:
    return [
        create_schema_tool(bigquery_client.schema_context()),
        create_query_tool(bigquery_client),
    ]
