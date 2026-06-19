import requests
from decouple import config

from apps.enrichment import documents


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
        return response.json()["choices"][0]["message"]["content"]

    def _build_prompt(self, transaction):

        rules = ", ".join(transaction.reasons) if transaction.reasons else "none"
        return (
            f"A payment transaction was flagged for review.\n\n"
            f"Amount: {transaction.amount} {transaction.currency}\n"
            f"Merchant: {transaction.merchant_name}\n"
            f"Location: {transaction.location}\n"
            f"Risk score: {transaction.risk_score}\n"
            f"Triggered rules: {rules}\n\n"
            f"In 2-3 sentences, explain why this transaction may be suspicious "
            f"and what a reviewer should look for."
        )
