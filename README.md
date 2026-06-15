# py-triage-engine

A Django REST API that receives payment webhook events and screens each
transaction through a deterministic rule engine, returning one of three
outcomes: AUTO_APPROVE, NEEDS_REVIEW, or AUTO_BLOCK.

## Why This Project

Built to learn Django and DRF end-to-end by solving a concrete problem.
The goal was to get the rule engine and synchronous request cycle right
before adding any moving parts.

That worked — until load testing revealed what happens when a slow
external call sits on the request thread.

## What's Implemented

- `POST /api/webhook/` validates and processes incoming transactions
- Rule engine with three rules evaluated per transaction:
  - AmountRule: blocks transactions above 50,000,000 IDR (weight 60)
  - FrequencyRule: flags users with more than 5 transactions in 10 minutes (weight 40)
  - GeoMismatchRule: flags location mismatch between transaction and user (weight 30)
- Score routing: score >= 60 AUTO_BLOCK, score >= 30 NEEDS_REVIEW, else AUTO_APPROVE
- Idempotency guard: duplicate requests with the same key return the cached result
- Custom User model extending AbstractUser
- GitHub Actions CI runs pytest on every push

## Load Test — Synchronous Path

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
is not to make the call faster — it is to move it off the request
thread entirely.

<details>
<summary>Locust screenshot</summary>

![sync_loadtest](./docs/benchmarks/sync_loadtest.png)

</details>

## Run Locally

```bash
docker compose up -d

pip install -r requirements.txt

cp .env.example .env

python manage.py migrate

python -m pytest apps/transactions/tests/ -v

python manage.py runserver
```