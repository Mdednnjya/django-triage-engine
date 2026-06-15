import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestWebhookView:

    def setup_method(self):
        self.client = APIClient()
        self.url = "/api/webhook/"
        # base payload
        self.payload = {
            "amount": 10_000,
            "currency": "IDR",
            "user_id": "user-view-1",
            "merchant_name": "Merchant A",
            "idempotency_key": "view-key-1",
        }

    def test_valid_payload_returns_200(self):

        response = self.client.post(self.url, self.payload, format="json")
        assert response.status_code == 200
        assert "status" in response.data

    def test_missing_required_field_returns_400(self):

        # drop amount
        payload = {k: v for k, v in self.payload.items() if k != "amount"}
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == 400

    def test_duplicate_idempotency_key_returns_same_transaction(self):

        first = self.client.post(self.url, self.payload, format="json")
        assert first.status_code == 200

        # duplicate
        second = self.client.post(self.url, self.payload, format="json")
        assert second.status_code == 200
        assert first.data["transaction_id"] == second.data["transaction_id"]
