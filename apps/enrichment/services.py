import json
import logging

import requests
from decouple import config

from apps.enrichment import documents

logger = logging.getLogger(__name__)


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class EnrichmentService:

    def enrich(self, transaction):

        explanation = self._call_llm(transaction)
        documents.update(
            transaction.id,
            "COMPLETED",
            explanation=explanation,
            model=config("OPENROUTER_MODEL", default="mistral/mistral-7b-instruct"),
        )

    def _call_llm(self, transaction):

        prompt = self._build_prompt(transaction)

        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {config('OPENROUTER_API_KEY', default='')}",
                "Content-Type": "application/json",
            },
            json={
                "model": config("OPENROUTER_MODEL", default="mistral/mistral-7b-instruct"),
                "messages": [{"role": "user", "content": prompt}],
                "stream": False, 
            },
            timeout=30,
        )


        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.error("malformed json from llm: %s", content)
            raise

    def _build_prompt(self, transaction):

        rules = ", ".join(transaction.reasons) if transaction.reasons else "none"
        return (
            f"A payment transaction was flagged for review.\n\n"
            f"Amount: {transaction.amount} {transaction.currency}\n"
            f"Merchant: {transaction.merchant_name}\n"
            f"Location: {transaction.location}\n"
            f"Risk score: {transaction.risk_score}\n"
            f"Triggered rules: {rules}\n\n"
            f"Respond with only valid JSON. No preamble, no markdown, no code fences.\n"
            f"Use this exact structure:\n"
            f'{{"summary": "brief one-line description of why this is flagged", '
            f'"risk_factors": ["factor 1", "factor 2"], '
            f'"recommended_action": "Hold and investigate / Monitor / Escalate", '
            f'"confidence": "low / medium / high"}}'
        )
