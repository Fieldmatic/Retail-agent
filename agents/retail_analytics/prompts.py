def build_sql_system_prompt(database_schema: str) -> str:
    return f"""
    Generate BigQuery Standard SQL for retail analytics.

    {database_schema}

    Return one query using fully qualified table names.
    Revenue means SUM(order_items.sale_price).
    """


REPORT_SYSTEM_PROMPT = """
You write concise executive retail analytics reports.
Use only the supplied query result rows. Do not invent data.
"""
