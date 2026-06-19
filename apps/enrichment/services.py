import json
import logging

import requests
from decouple import config

from apps.enrichment import documents

logger = logging.getLogger(__name__)


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_SYSTEM_PROMPT = (
    "You are a financial risk analyst reviewing flagged transactions. "
    "Always respond with valid JSON only. No preamble, no markdown, "
    "no code fences, no explanation outside the JSON object. "
    "Never deviate from the required structure: "
    '{"summary": "...", "risk_factors": [...], "recommended_action": "...", "confidence": "..."} '
    "confidence definition: "
    "high: risk_score >= 50 or critical rule triggered; "
    "medium: risk_score 30-49, multiple rules triggered; "
    "low: borderline score, single rule triggered"
)


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
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
            timeout=30,
        )


        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()

        # strip markdown code fences if model ignores instruction
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

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
            f"Triggered rules: {rules}"
        )
