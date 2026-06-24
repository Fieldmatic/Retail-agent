from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class SqlPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sql: str


class SqlValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    sql: str | None = None
    error: str | None = None


class QueryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: list[dict[str, Any]]
    bytes_processed: int


class QueryError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: Literal["planning", "validation", "bigquery"]
    message: str
