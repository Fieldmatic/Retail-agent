# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
# -- google-cloud-bigquery Row objects expose dynamic, untyped attribute access
from google.cloud import bigquery

from agents.retail_analytics.schemas import QueryResult
from core.settings import Settings

DATASET = "bigquery-public-data.thelook_ecommerce"
ALLOWED_TABLE_NAMES = {"orders", "order_items", "products", "users"}


class BigQueryClient:
    def __init__(self, settings: Settings) -> None:
        self.client = bigquery.Client(project=settings.google_cloud_project)
        self.max_bytes_billed = settings.bigquery_max_bytes_billed

    def schema_context(self) -> str:
        table_names = ", ".join(f"'{table}'" for table in sorted(ALLOWED_TABLE_NAMES))
        sql = f"""
            SELECT table_name, column_name, data_type
            FROM `{DATASET}.INFORMATION_SCHEMA.COLUMNS`
            WHERE table_name IN ({table_names})
            ORDER BY table_name, ordinal_position
        """

        columns_by_table: dict[str, list[str]] = {}
        for row in self.client.query(sql).result():
            columns_by_table.setdefault(row.table_name, []).append(
                f"{row.column_name} {row.data_type}"
            )

        lines = [f"Dataset: `{DATASET}`", "Tables:"]
        for table_name, columns in columns_by_table.items():
            lines.append(f"- {table_name}({', '.join(columns)})")
        return "\n".join(lines)

    def dry_run(self, sql: str) -> int:
        job = self.client.query(
            sql,
            job_config=bigquery.QueryJobConfig(
                dry_run=True,
                use_query_cache=False,
                maximum_bytes_billed=self.max_bytes_billed,
            ),
        )
        return job.total_bytes_processed or 0

    def query(self, sql: str) -> QueryResult:
        bytes_processed = self.dry_run(sql)
        job = self.client.query(
            sql,
            job_config=bigquery.QueryJobConfig(maximum_bytes_billed=self.max_bytes_billed),
        )
        return QueryResult(
            rows=[dict(row) for row in job.result()], bytes_processed=bytes_processed
        )
