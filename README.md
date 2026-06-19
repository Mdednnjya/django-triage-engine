# py-triage-engine

A Django REST API that receives payment webhook events, screens each transaction through a deterministic rule engine, then asynchronously enriches flagged transactions with an LLM-generated explanation for human reviewers.

## Why This Project

Built to learn Django and DRF end-to-end by solving a concrete, real-sounding problem. The synchronous rule engine came first; the async enrichment path was added after seeing how a blocking LLM call would degrade webhook response time.

## What's Implemented

- `POST /api/webhook/` validates and processes incoming transactions, returns 202
- Rule engine with three rules evaluated per transaction:
  - AmountRule: blocks transactions above 50,000,000 IDR (weight 60)
  - FrequencyRule: flags users with more than 5 transactions in 10 minutes (weight 40)
  - GeoMismatchRule: flags location mismatch between transaction and user (weight 30)
- Score routing: score >= 60 AUTO_BLOCK, score >= 30 NEEDS_REVIEW, else AUTO_APPROVE
- Idempotency guard: duplicate requests with the same key return the cached result
- Flagged transactions (NEEDS_REVIEW, AUTO_BLOCK) are enqueued to Celery via Redis
- Celery worker calls OpenRouter LLM and saves the explanation to MongoDB
- `GET /api/dashboard/` returns flagged transactions with their LLM explanations
- Custom User model extending AbstractUser
- GitHub Actions CI runs pytest on every push

## Run Locally

```bash
docker compose up -d

pip install -r requirements.txt

cp .env.example .env

python manage.py migrate

# run the worker in a separate terminal
celery -A config worker --loglevel=info

python -m pytest apps/ -v

python manage.py runserver
```
