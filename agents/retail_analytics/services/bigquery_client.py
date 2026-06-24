# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
# -- google-cloud-bigquery Row objects expose dynamic, untyped attribute access
from google.api_core.retry import Retry
from google.cloud import bigquery

from agents.retail_analytics.schemas import QueryResult
from core.settings import Settings

DATASET = "bigquery-public-data.thelook_ecommerce"
ALLOWED_TABLE_NAMES = {"orders", "order_items", "products", "users"}

TRANSIENT_RETRY = Retry(initial=0.5, maximum=4.0, multiplier=2.0, timeout=10.0)


class BigQueryClient:
    def __init__(self, settings: Settings) -> None:
        self.client = bigquery.Client(project=settings.google_cloud_project)
        self.max_bytes_billed = settings.bigquery_max_bytes_billed

    def schema_context(self) -> str:
        lines = [f"Dataset: `{DATASET}`", "Tables:"]
        for table_name in sorted(ALLOWED_TABLE_NAMES):
            table = self.client.get_table(f"{DATASET}.{table_name}", retry=TRANSIENT_RETRY)
            columns = ", ".join(f"{field.name} {field.field_type}" for field in table.schema)
            lines.append(f"- {table_name}({columns})")
        return "\n".join(lines)

    def dry_run(self, sql: str) -> int:
        job = self.client.query(
            sql,
            job_config=bigquery.QueryJobConfig(
                dry_run=True,
                use_query_cache=False,
                maximum_bytes_billed=self.max_bytes_billed,
            ),
            retry=TRANSIENT_RETRY,
        )
        return job.total_bytes_processed or 0

    def query(self, sql: str) -> QueryResult:
        bytes_processed = self.dry_run(sql)
        job = self.client.query(
            sql,
            job_config=bigquery.QueryJobConfig(maximum_bytes_billed=self.max_bytes_billed),
            retry=TRANSIENT_RETRY,
        )
        return QueryResult(
            rows=[dict(row) for row in job.result()], bytes_processed=bytes_processed
        )
