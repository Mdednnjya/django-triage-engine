import pytest
from apps.transactions.services import TransactionService


@pytest.mark.django_db
class TestTransactionService:

    def test_process_creates_transaction(self):

        service = TransactionService()
        tx_data = {
            "amount": 10_000,
            "currency": "IDR",
            "user_id": "user-1",
            "merchant_name": "Merchant A",
            "idempotency_key": "idem-1",
        }

        transaction = service.process(tx_data, "idem-1")

        assert transaction.status == "AUTO_APPROVE"
        assert transaction.idempotency_key == "idem-1"

    def test_idempotent_on_duplicate_key(self):

        service = TransactionService()
        tx_data = {
            "amount": 10_000,
            "currency": "IDR",
            "user_id": "user-1",
            "merchant_name": "Merchant A",
            "idempotency_key": "idem-2",
        }

        first = service.process(tx_data, "idem-2")
        second = service.process(tx_data, "idem-2")

        assert first.id == second.id

    def test_auto_blocks_high_amount(self):

        service = TransactionService()
        tx_data = {
            "amount": 60_000_000,
            "currency": "IDR",
            "user_id": "user-2",
            "merchant_name": "Merchant B",
            "idempotency_key": "idem-3",
        }

        transaction = service.process(tx_data, "idem-3")

        assert transaction.status == "AUTO_BLOCK"
        assert transaction.risk_score >= 60
