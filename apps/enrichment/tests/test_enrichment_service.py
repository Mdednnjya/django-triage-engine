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
            "choices": [{"message": {"content": '{"summary": "High amount transaction", "risk_factors": ["amount exceeds threshold"], "recommended_action": "Hold and investigate", "confidence": "high"}'}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("apps.enrichment.services.requests.post", return_value=mock_response):
            with patch("apps.enrichment.documents.update") as mock_update:

                # call
                service = EnrichmentService()
                service.enrich(transaction)

                mock_update.assert_called_once_with(
                    transaction.id,
                    "COMPLETED",
                    explanation={
                        "summary": "High amount transaction",
                        "risk_factors": ["amount exceeds threshold"],
                        "recommended_action": "Hold and investigate",
                        "confidence": "high",
                    },
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

    def test_enrich_sets_pending_when_circuit_open(self):

        from apps.transactions.models import Transaction

        # seed
        transaction = Transaction.objects.create(
            amount=60_000_000,
            currency="IDR",
            user_id="user-enrich-3",
            merchant_name="Merchant Z",
            status="NEEDS_REVIEW",
            risk_score=40,
            reasons=["location mismatch"],
            idempotency_key="enrich-key-3",
        )

        with patch("apps.enrichment.circuit_breaker.allow_request", return_value=False):
            with patch("apps.enrichment.documents.update_status_if_not_terminal") as mock_update:
                with patch("apps.enrichment.services.requests.post") as mock_post:

                    # call
                    service = EnrichmentService()
                    service.enrich(transaction)

                    mock_update.assert_called_once_with(transaction.id, "PENDING")
                    mock_post.assert_not_called()

    def test_enrich_records_failure_and_reraises_on_llm_error(self):

        from apps.transactions.models import Transaction

        # seed
        transaction = Transaction.objects.create(
            amount=60_000_000,
            currency="IDR",
            user_id="user-enrich-4",
            merchant_name="Merchant Z",
            status="NEEDS_REVIEW",
            risk_score=40,
            reasons=["location mismatch"],
            idempotency_key="enrich-key-4",
        )

        with patch("apps.enrichment.circuit_breaker.allow_request", return_value=True):
            with patch("apps.enrichment.circuit_breaker.record_failure") as mock_record_fail:
                with patch("apps.enrichment.services.requests.post", side_effect=Exception("timeout")):

                    # checker
                    service = EnrichmentService()
                    with pytest.raises(Exception, match="timeout"):
                        service.enrich(transaction)

                    mock_record_fail.assert_called_once()

    def test_enrich_records_success_on_completed(self):

        from apps.transactions.models import Transaction

        # seed
        transaction = Transaction.objects.create(
            amount=60_000_000,
            currency="IDR",
            user_id="user-enrich-5",
            merchant_name="Merchant Z",
            status="NEEDS_REVIEW",
            risk_score=40,
            reasons=["location mismatch"],
            idempotency_key="enrich-key-5",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"summary": "test", "risk_factors": [], "recommended_action": "approve", "confidence": "low"}'}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("apps.enrichment.circuit_breaker.allow_request", return_value=True):
            with patch("apps.enrichment.circuit_breaker.record_success") as mock_record_success:
                with patch("apps.enrichment.services.requests.post", return_value=mock_response):
                    with patch("apps.enrichment.documents.update") as mock_update:

                        # call
                        service = EnrichmentService()
                        service.enrich(transaction)

                        mock_record_success.assert_called_once()
                        mock_update.assert_called_once()
