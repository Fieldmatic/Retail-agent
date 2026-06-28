# Requirements

This document maps the assignment requirements to the production design. The README and
Architecture document describe the prototype scope.

## 1. Hybrid Intelligence

The agent grounds each answer in the Golden Knowledge Bucket, not SQL alone. The bucket stores
human approved Trios:

```text
Question -> SQL Query -> Analyst Report
```

**Relevant data at query time.** Each approved Trio is embedded by its question text with a Vertex
AI embedding model and stored in the Vector Store with metadata: source tables, business measure
(revenue, order count, margin), time range, and data watermark. On a request the agent embeds the
question, retrieves the top 3 to 5 nearest Trios that share source tables, and loads the full Trios
from GCS. A similarity floor prevents weak matches from being injected. The Trios show how analysts
handled similar questions: metric choice, joins, and report framing. They are examples, not answers.

**Updating the bucket over time.** The bucket is curated by humans. Analysts can upload historical
Trios or create new ones manually. Generated reports become draft candidates only after a human
signal, such as a manager saving or rating a report, or an analyst reviewing sampled traffic.
Questions with no close Trio become coverage gaps. A human approves, edits, or rejects each
candidate before it is versioned, embedded, and made retrievable.

## 2. Safety and PII Masking

The classifier refuses unrelated, hostile, jailbreak, and direct PII extraction requests, and
routes saved report delete requests to the confirmation flow (#3). Routing uses structured output
(a typed `RequestCategory` enum), not free text parsing. The delete flow (#3) uses the same pattern
to extract its request. Analytics requests can only reach BigQuery through `run_validated_query`.
(The prototype has only the analytics and refusal paths, so delete requests are refused there.)

That tool:

- Parses SQL with `sqlglot`.
- Allows one `SELECT` or `WITH` query.
- Restricts access to the assigned `thelook_ecommerce` tables.
- Rejects `SELECT *`.
- Caps returned rows when the query has no explicit limit.
- Runs a BigQuery dry run with `maximum_bytes_billed`.
- Executes the query.
- Masks sensitive columns and email/phone patterns before rows return to the agent.

Two masking layers are used: column name masking covers known PII columns, and the value level
email/phone regex catches aliases (`SELECT email AS note`) or PII inside free text fields. The tool
always validates, executes, then masks before rows return to the agent, so the model never receives
an unmasked row.

PII is handled in tiers, not as a flat blocklist: hard contact identifiers (email, phone) and
precise location (street address, coordinates) are always masked; coarse geo (city, state, country)
stays visible as an aggregation dimension; customer identity (name) is left visible so "top
customers" analysis works, and would be gated by role in production.

Safety does not depend on the classifier being right: a misrouted request still hits
`run_validated_query` (read only, allow listed, masked), so the structural guards hold regardless.
Prompt injection hidden in row data is contained by the same controls: the data is read only, PII is
already masked, and the agent only summarizes it.

Authentication is required by default in production clients, and secrets live in Secret Manager or
environment variables, never in prompts or code.

## 3. High Stakes Oversight

The analytics database is read only, but saved reports are mutable application data owned by users.
Delete requests do not run through the analyst agent or a ReAct loop.

Saved report metadata lives in Postgres: `id`, `owner_id`, `title`, `created_at`, `deleted_at`, and
the GCS object path. Report bodies live in GCS. Postgres stores searchable metadata or extracted text
for matching delete requests.

Destructive flow:

1. Extract the delete intent and filters into typed fields.
2. Resolve owned matching reports by title/content match and date filters (e.g. "today" in the
   user's timezone).
3. Show the exact target count and representative titles.
4. Require explicit confirmation.
5. Execute as an idempotent soft delete with an audit record.
6. Return the result to the user.

The confirmation gate is a LangGraph `interrupt`: the graph pauses after showing the targets,
persists state, and resumes only on explicit approval. A refresh or disconnect can't partly execute a
delete. The LLM only extracts intent or asks a clarifying question; resolution, ownership, the gate,
execution, and audit logging stay deterministic, and a user can delete only their own reports. The
audit record captures actor, filter, matched ids, and outcome. The same pattern extends to other
saved report mutations later.

## 4. Continuous Improvement

Continuous improvement is a memory problem at three layers.

**Conversation memory (short term).** Within a session the agent remembers the dialogue, so a
manager can ask follow ups ("now break that down by month") without repeating context. LangGraph's
checkpointer holds this, keyed by thread/user id.

**User memory (long term preferences).** A manager profile remembers answer style, such as
Manager A preferring tables and Manager B preferring bullets. It also stores level of detail, common
regions/stores, and saved report habits. Preferences are set explicitly ("always answer with
tables") or inferred from repeated feedback, then injected into the prompt by user id.

**System memory (learning from past interactions).** The Golden Knowledge Bucket (#1) is the
system's long term memory: curated past interactions that shape future answers.

Feedback updates these layers on different paths. Explicit user preferences can update the
manager profile. Low ratings, repeated SQL repairs, empty results, and questions with no close
Trio become review signals for analysts. They do not automatically change the Golden Bucket; they
create candidates or coverage gaps that a human reviews before anything becomes reusable knowledge.

## 5. Resilience and Graceful Error Handling

The system handles common failures without crashing the CLI or wasting unbounded model calls:

- SQL validation errors return tool errors the agent can repair.
- BigQuery errors return tool errors the agent can repair.
- Empty results return `NO_ROWS`; the prompt nudges the agent to broaden the query before
  concluding no data.
- BigQuery calls use bounded transient retries with exponential backoff (capped).
- Dry runs enforce a cost cap before execution.
- Self correction is bounded by the graph recursion limit, so repair attempts cannot run forever.
- BigQuery dry runs and `maximum_bytes_billed` cap cost before any query executes.
- CLI startup, rate limit, and provider unavailable errors return messages the user can act on.

Production adds provider circuit breakers with failover to a secondary model/provider (e.g.
OpenRouter) on sustained downtime, cached schema context, alerting on repeated failures, and queued
delivery for report generation that does not need an immediate response.

## 6. Quality Assurance

The eval set is built two ways: held out Golden Trios give labeled ground truth (each Trio is a
question, expected SQL, and expected report), and written cases cover what Trios won't: unsafe, PII,
jailbreak requests, empty results, and SQL repair paths.

The eval runner executes the full agent and reads the trace for each case: retrieved Trio ids,
generated SQL, validation result, masked rows, tool errors, and final answer. Checks are concrete:

- For "top products by revenue", SQL must use the allowed order/product tables, stay under the cost
  cap, and every number in the answer must exist in returned rows.
- For "which region is underperforming", the answer must include the requested comparison and must
  not invent a reason that is not present in the data.
- For customer personal data requests, the final answer must not leak email, phone, street address,
  or precise location (coordinates).
- For saved report deletes, the trace must show target resolution and confirmation before any
  delete executes.

Deterministic checks cover SQL shape, table allow list, cost caps, PII regexes, row/answer numeric
grounding, and whether the delete step ran before approval. An LLM judge with a fixed rubric scores
the subjective parts, mainly intent match and report usefulness, with sampled human review.

Ragas is useful as an add on, not the main gate. It can score retrieval and reporting quality:
whether the retrieved Trios are relevant, whether the answer is grounded in returned rows, and
whether the report addresses the question. The hard gates above still decide pass/fail before
deployment. After deployment, the same grounding and personal data leak checks run on sampled live
traffic through the #7 traces.

An eval run fails if any personal data case leaks, if generated SQL escapes the table allow list, if
a delete executes without confirmation, or if answer numbers are not present in returned rows.

## 7. Observability

Each run is traced (LangSmith or Langfuse, with OpenTelemetry spans per graph node and tool) under
one trace id, recording each step's inputs and outputs: classification, retrieved Trio ids and
scores, tool calls by tool name, generated SQL and validation result, bytes billed, retries, model
calls and token usage, PII masking count, refusal reason, and any delete target count plus
confirmation result.

Core metrics:

- success and refusal rates
- tool call count by tool
- tool failure count by tool
- provider error rate
- p95 latency, token usage, model cost, and BigQuery bytes billed per answer
- PII masking hits
- delete approvals vs cancellations
- grounding failures and sampled eval scores

The full message/tool correspondence is replayable from the trace for deep debugging. Only
masked rows are stored, never raw PII.

## 8. Persona Management

Report tone and formatting live in a versioned prompt registry in Postgres. Business users can edit
the active persona in a small internal editor, publish it without redeploying, and roll back if a
change hurts answer quality. Each run records the persona version in the trace.

The persona only controls voice and formatting. Safety rules stay in base instructions owned by the
app, so a persona edit cannot disable PII masking or the analysis only guardrail. At runtime the app
composes the base instructions, active persona, user preferences, and Golden Trio context.
