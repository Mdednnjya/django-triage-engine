# py-triage-engine

A Django REST API that receives payment webhook events and screens each transaction through a deterministic rule engine, returning one of three outcomes: AUTO_APPROVE, NEEDS_REVIEW, or AUTO_BLOCK.

## Why This Project

Built to learn Django and DRF end-to-end by solving a concrete, real-sounding problem. The goal is to get the rule engine and request cycle right before adding any moving parts.

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

## Run Locally

```bash
docker compose up -d

pip install -r requirements.txt

cp .env.example .env

python manage.py migrate

python -m pytest apps/transactions/tests/ -v

python manage.py runserver
```
