import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from agents.retail_analytics.schemas import SqlValidationResult
from agents.retail_analytics.services.bigquery_client import ALLOWED_TABLE_NAMES, DATASET


def validate_sql(sql: str) -> SqlValidationResult:
    try:
        expressions = sqlglot.parse(sql, read="bigquery")
    except SqlglotError as error:
        return SqlValidationResult(valid=False, error=f"SQL parse error: {error}")

    if len(expressions) != 1:
        return SqlValidationResult(valid=False, error="SQL must contain exactly one statement.")

    expression = expressions[0]
    if not isinstance(expression, exp.Select):
        return SqlValidationResult(valid=False, error="Only SELECT/WITH queries are allowed.")

    cte_names = {cte.alias for cte in expression.find_all(exp.CTE)}
    for table in expression.find_all(exp.Table):
        if table.name in cte_names:
            continue
        if f"{table.catalog}.{table.db}" != DATASET or table.name not in ALLOWED_TABLE_NAMES:
            return SqlValidationResult(valid=False, error=f"Table is not allowed: {table}")

    for select in expression.find_all(exp.Select):
        for projection in select.expressions:
            if isinstance(projection, exp.Star) or (
                isinstance(projection, exp.Column) and projection.name == "*"
            ):
                return SqlValidationResult(valid=False, error="SELECT * is not allowed.")

    safe_sql = expression.sql(dialect="bigquery")
    if not expression.args.get("limit"):
        safe_sql = f"{safe_sql} LIMIT 100"

    return SqlValidationResult(valid=True, sql=safe_sql)
