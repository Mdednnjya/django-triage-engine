# py-triage-engine

A Django REST API that receives payment webhook events and screens each
transaction through a deterministic rule engine, returning one of three
outcomes: AUTO_APPROVE, NEEDS_REVIEW, or AUTO_BLOCK. Flagged transactions
are enriched asynchronously with an LLM-generated explanation for human
reviewers.

## Why This Project

Built to learn Django and DRF end-to-end by solving a concrete problem.
The goal was to get the rule engine and synchronous request cycle right
before adding any moving parts.

That worked until load testing revealed what happens when a slow
external call sits on the request thread. Under 500 concurrent users,
87.9% of requests failed. The fix was not to make the call faster; it
was to move it off the request thread entirely.

## Architecture

Request flow with layered separation:
- View — HTTP handler, validates request, returns 202 immediately
- Service — rule engine evaluation, idempotency check, enqueue logic
- Task — Celery async worker, LLM call, enrichment persistence
- Repository — PostgreSQL via Django ORM, MongoDB via pymongo

## Tech Stack

Python 3.12 · Django 5 · Django REST Framework · Celery · Redis · PostgreSQL · MongoDB · Docker · Docker Compose


## What's Implemented

- `POST /api/webhook/` — rule engine screens each transaction; returns 202 immediately
- Rule engine: AmountRule, FrequencyRule, GeoMismatchRule; deterministic score routing
- Idempotency guard with select_for_update; duplicate webhooks blocked at DB level
- Celery async worker decouples LLM enrichment from request thread
- LLM explanation stored as structured JSON in MongoDB; QUEUED; PROCESSING; COMPLETED; FAILED; PENDING
- Polyglot persistence: PostgreSQL for transactions; MongoDB for enrichment documents
- `GET /api/dashboard/` joins both stores at application layer

## Engineering Decisions

| Failure Mode | Without Fix | Solution |
|---|---|---|
| LLM call blocks request thread | 87.9% errors under 500 concurrent users | Celery async worker; API returns 202 immediately |
| Same webhook delivered twice | Two enrichment tasks run concurrently; duplicate MongoDB documents | select_for_update on enrichment_queued flag; second enqueue blocked at DB level |
| Celery retries exhausted silently | Transaction stays QUEUED forever; dashboard shows stale state | Catch retry exhaustion explicitly; write FAILED status to MongoDB |
| Enrichment result schema varies per transaction type | Nullable columns or multiple tables in relational DB | MongoDB document store; flexible schema per enrichment document |
| LLM returns free-form text | Unparseable by downstream systems | System prompt constrains output to structured JSON with defined fields |

## Enrichment Output

LLM explanation is stored as structured JSON, not free-form text:

```json
{
  "summary": "Large transaction with a suspicious merchant in Bali.",
  "risk_factors": ["amount exceeds threshold", "suspicious merchant"],
  "recommended_action": "Block the transaction and investigate further.",
  "confidence": "high"
}
```

<details>
<summary>Dashboard response — enrichment COMPLETED</summary>

![dashboard_completed](./docs/benchmarks/async-enrichment/dashboard_completed.png)

</details>

## Load Test — Synchronous Path (before fix)

Simulated a slow external call (2s latency) on the request thread to
measure behavior under concurrent load. 500 concurrent users, 50/s ramp.

| Metric | Result |
|---|---|
| Total requests | 2,742 |
| Failures | 2,409 (87.9%) |
| Avg latency | 20,334ms |
| Median latency | 27,000ms |
| 99th percentile | 37,000ms |
| RPS | 17.1 |

Key finding: a 2-second blocking call on the request thread causes
87.9% of requests to fail under 500 concurrent users. Thread pool
exhaustion means most requests never reach the rule engine. The fix
is not to make the call faster; it is to move it off the request
thread entirely.

<details>
<summary>Locust screenshot</summary>

![sync_loadtest](./docs/benchmarks/sync/sync_loadtest.png)

</details>

## Real-World Behavior — OpenRouter Rate Limiting

Under concurrent load, the free-tier LLM API returned 429 Too Many
Requests. The worker retried with 60s backoff but continued hitting
the rate limit. This is the production scenario that motivates the
next layer: instead of blind retrying against a throttled dependency,
detect the failure pattern and stop hammering it.

<details>
<summary>Worker log — 429 retry loop</summary>

![worker_429_retry](./docs/benchmarks/async-enrichment/worker_429_retry.png)

</details>

<details>
<summary>Worker log — successful enrichment</summary>

![worker_success](./docs/benchmarks/async-enrichment/worker_success.png)

</details>

## Run Locally

```bash
docker compose up --build

cp .env.example .env
# fill in OPENROUTER_API_KEY and OPENROUTER_MODEL in .env

python -m pytest apps/ -v
```