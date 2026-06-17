import pytest
from unittest.mock import patch, MagicMock, ANY

from apps.enrichment.services import EnrichmentService


@pytest.mark.django_db
class TestEnrichmentService:

    def test_enrich_calls_llm_and_saves(self):

        from apps.transactions.models import Transaction

        # seed
        transaction = Transaction.objects.create(
            amount=60_000_000,
            currency="IDR",
            user_id="user-enrich-1",
            merchant_name="Merchant X",
            status="AUTO_BLOCK",
            risk_score=60,
            reasons=["amount exceeds threshold"],
            idempotency_key="enrich-key-1",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Suspicious due to high amount."}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("apps.enrichment.services.requests.post", return_value=mock_response):
            with patch("apps.enrichment.documents.save") as mock_save:

                # call
                service = EnrichmentService()
                service.enrich(transaction)

                mock_save.assert_called_once_with(
                    transaction_id=transaction.id,
                    explanation="Suspicious due to high amount.",
                    status="DONE",
                    model=ANY,
                )

    def test_enrich_raises_on_llm_failure(self):

        from apps.transactions.models import Transaction

        # seed
        transaction = Transaction.objects.create(
            amount=60_000_000,
            currency="IDR",
            user_id="user-enrich-2",
            merchant_name="Merchant Y",
            status="NEEDS_REVIEW",
            risk_score=30,
            reasons=["location mismatch"],
            idempotency_key="enrich-key-2",
        )

        with patch("apps.enrichment.services.requests.post", side_effect=Exception("timeout")):

            # checker
            service = EnrichmentService()
            with pytest.raises(Exception, match="timeout"):
                service.enrich(transaction)
