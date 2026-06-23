import pytest
from unittest.mock import patch


@pytest.mark.django_db
class TestEnrichTransaction:

    def test_saves_failed_status_when_retries_exhausted(self):

        from apps.transactions.models import Transaction
        from apps.enrichment.tasks import enrich_transaction

        # seed
        transaction = Transaction.objects.create(
            amount=60_000_000,
            currency="IDR",
            user_id="user-task-1",
            merchant_name="Merchant Z",
            status="NEEDS_REVIEW",
            risk_score=30,
            reasons=["location mismatch"],
            idempotency_key="task-key-1",
        )

        with patch("apps.enrichment.services.EnrichmentService.enrich", side_effect=Exception("timeout")):
            with patch("apps.enrichment.documents.update") as mock_update:
                enrich_transaction.apply(args=[str(transaction.id)])

                mock_update.assert_any_call(str(transaction.id), "FAILED")
