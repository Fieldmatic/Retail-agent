from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class QueryStage(StrEnum):
    PLANNING = "planning"
    VALIDATION = "validation"
    BIGQUERY = "bigquery"
    EMPTY = "empty"


class RequestCategory(StrEnum):
    ANALYTICS = "analytics"
    OFF_TOPIC = "off_topic"


class RequestClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: RequestCategory


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

    stage: QueryStage
    message: str
