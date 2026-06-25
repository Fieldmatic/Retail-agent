from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class RequestCategory(StrEnum):
    ANALYTICS = "analytics"
    OFF_TOPIC = "off_topic"


class RequestClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: RequestCategory


class SqlValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    sql: str | None = None
    error: str | None = None


class QueryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: list[dict[str, Any]]
    bytes_processed: int
