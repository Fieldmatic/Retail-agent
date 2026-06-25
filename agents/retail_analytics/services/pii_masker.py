import re
from typing import Any

EMAIL_RE = re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?<!\w)(?:\+\d[\d\s().-]{7,}\d|\(\d{3}\)\s?\d{3}[-.\s]?\d{4}|\d{3}[-.\s]\d{3}[-.\s]\d{4})(?!\w)"
)

SENSITIVE_COLUMNS = {
    "email",
    "phone",
    "first_name",
    "last_name",
    "street_address",
    "latitude",
    "longitude",
    "user_geom",
}


def redact_pii(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    redacted_rows: list[dict[str, Any]] = []

    for row in rows:
        redacted_row: dict[str, Any] = {}
        for key, value in row.items():
            if key.lower() in SENSITIVE_COLUMNS:
                redacted_row[key] = "[REDACTED]"
            elif isinstance(value, str):
                value = EMAIL_RE.sub("[REDACTED_EMAIL]", value)
                value = PHONE_RE.sub("[REDACTED_PHONE]", value)
                redacted_row[key] = value
            else:
                redacted_row[key] = value
        redacted_rows.append(redacted_row)

    return redacted_rows
