import pytest
from unittest.mock import patch
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestWebhookView:

    def setup_method(self):
        self.client = APIClient()
        self.url = "/api/webhook/"
        self.payload = {
            "amount": 10_000,
            "currency": "IDR",
            "user_id": "user-view-1",
            "merchant_name": "Merchant A",
            "idempotency_key": "view-key-1",
        }
        self.flagged_payload = {
            "amount": 60_000_000,
            "currency": "IDR",
            "user_id": "user-view-2",
            "merchant_name": "Merchant B",
            "idempotency_key": "view-key-flagged",
        }

    def test_valid_payload_returns_202(self):

        response = self.client.post(self.url, self.payload, format="json")
        assert response.status_code == 202
        assert "status" in response.data

    def test_missing_required_field_returns_400(self):

        # drop amount
        payload = {k: v for k, v in self.payload.items() if k != "amount"}
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == 400

    def test_duplicate_idempotency_key_returns_same_transaction(self):

        with patch("apps.enrichment.tasks.enrich_transaction.delay"):
            first = self.client.post(self.url, self.flagged_payload, format="json")
            assert first.status_code == 202

            # duplicate
            second = self.client.post(self.url, self.flagged_payload, format="json")
            assert second.status_code == 202
            assert first.data["transaction_id"] == second.data["transaction_id"]

    def test_duplicate_webhook_does_not_double_enqueue(self):

        with patch("apps.enrichment.tasks.enrich_transaction.delay") as mock_delay:
            self.client.post(self.url, self.flagged_payload, format="json")

            # duplicate
            self.client.post(self.url, self.flagged_payload, format="json")

            # enrich_transaction.delay called exactly once
            assert mock_delay.call_count == 1
