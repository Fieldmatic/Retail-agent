# Retail AI Data Assistant

CLI prototype for a LangGraph-based retail analytics assistant. Answers questions
against the public `bigquery-public-data.thelook_ecommerce` dataset.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) and Python 3.13
- A Google Cloud project with the BigQuery API enabled, and Application Default
  Credentials for BigQuery access:

  ```bash
  gcloud auth application-default login
  ```

## Setup

```bash
make setup
```

Configure `.env`. The LLM runs in one of two modes:

- **API key** (default): set `GOOGLE_API_KEY`.
- **Vertex AI**: set `USE_VERTEX_AI=true` and `GOOGLE_CLOUD_PROJECT` (uses your
  gcloud credentials, no API key needed).

```env
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
USE_VERTEX_AI=false
VERTEX_AI_LOCATION=us-central1
GOOGLE_CLOUD_PROJECT=
BIGQUERY_MAX_BYTES_BILLED=1000000000
```

## Run

```bash
make start
```

## Check

```bash
make check
make format
```
