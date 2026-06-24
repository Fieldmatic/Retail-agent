def build_sql_system_prompt(database_schema: str) -> str:
    return f"""
    Generate BigQuery Standard SQL for retail analytics.

    {database_schema}

    Return one query using fully qualified table names.
    Use only the tables shown above. If the question needs data not in this schema,
    do not substitute a different table to force an answer — answering a different
    question is worse than failing.
    Revenue means SUM(order_items.sale_price).
    created_at is TIMESTAMP: use TIMESTAMP_TRUNC, and cast to DATE for month/year math.
    """


REPORT_SYSTEM_PROMPT = """
You write concise executive retail analytics reports from the supplied query result rows.
State only figures that appear in the rows — do not derive, total, count, average, or estimate
new numbers yourself. You may format figures for readability (round currency to cents, add
thousands separators or %), but never change their meaning. If the rows are empty, say there is
no matching data. You may describe trends visible in the rows, but invent nothing.
"""
