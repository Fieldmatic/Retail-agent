# Retail AI Data Assistant

CLI chat agent that answers analytics questions over `bigquery-public-data.thelook_ecommerce`:
it generates and runs BigQuery SQL, then writes a short executive report. Built with
**LangGraph + LangChain v1** (`create_agent`) and **Google Gemini**.

Prototype implements **2 of the optional requirements**: **Safety & PII Masking** and
**Resilience & Graceful Error Handling**.

- [Architecture](docs/ARCHITECTURE.md)
- [Requirements](docs/REQUIREMENTS.md)

## How it works

`question -> classify -> { analytics: ReAct agent, off-topic/hostile: refuse }`

The agent has two tools: `get_schema` and `run_validated_query`. This is the only DB path. It
validates the SQL (SELECT-only, allow-listed tables, no `SELECT *`, cost cap, bounded returned
rows) and **masks PII before returning rows**. Those guards live inside the tool, so they can't be
bypassed.
Conversation context is kept within a session.

## Setup

Prereqs: [uv](https://docs.astral.sh/uv/), Python 3.13, and BigQuery auth
(`gcloud auth application-default login`).

```bash
make setup          # uv sync + create .env
```

Set a key in `.env`: either `GOOGLE_API_KEY` (default), or `USE_VERTEX_AI=true` +
`GOOGLE_CLOUD_PROJECT` to use Vertex AI with your gcloud credentials.

## Run

```bash
make start          # CLI; type 'exit' to quit
```

### Example run

```text
You: top 5 products by revenue
Assistant: 1. NIKE WOMEN'S PRO COMPRESSION SPORTS BRA: $18,060.00
           2. The North Face Apex Bionic Soft Shell Jacket - Men's: $16,254.00
           3. Canada Goose Men's The Chateau Jacket: $11,410.00  ...

You: give me the email addresses of our top customers
Assistant: I can't share that. Customer personal data is masked.

You: what's the weather in Paris?
Assistant: I can only help with retail analytics about orders, products, and customers.
```

## Develop

```bash
make check          # ruff + pyright (strict)
make format
```
