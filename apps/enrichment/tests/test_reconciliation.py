import time

import fakeredis
import pytest
from unittest.mock import patch

import apps.enrichment.circuit_breaker as cb
from apps.enrichment.reconciliation import reconcile_pending


@pytest.fixture(autouse=True)
def fake_redis_cb(monkeypatch):
    server = fakeredis.FakeServer()
    r = fakeredis.FakeRedis(server=server)
    monkeypatch.setattr(cb, "_r", lambda: r)
    yield r
    r.flushall()


class TestReconcilePending:

    def test_exits_when_no_pending(self, fake_redis_cb):

        with patch("apps.enrichment.documents.find_pending_older_than", return_value=[]):
            with patch("apps.enrichment.circuit_breaker.allow_request") as mock_allow:
                with patch("apps.enrichment.tasks.enrich_transaction") as mock_task:

                    reconcile_pending()

                    mock_allow.assert_not_called()
                    mock_task.delay.assert_not_called()

    def test_skips_requeue_when_circuit_open(self, fake_redis_cb):

        # seed
        fake_redis_cb.hset(cb._KEY, mapping={
            "state": "OPEN",
            "failure_count": 3,
            "last_failure_at": str(time.time()),
        })
        pending = [{"transaction_id": "tx-recon-1"}, {"transaction_id": "tx-recon-2"}]

        with patch("apps.enrichment.documents.find_pending_older_than", return_value=pending):
            with patch("apps.enrichment.documents.update_status_if_not_terminal") as mock_update:
                with patch("apps.enrichment.tasks.enrich_transaction") as mock_task:

                    reconcile_pending()

                    mock_update.assert_not_called()
                    mock_task.delay.assert_not_called()

    def test_requeues_all_pending_when_circuit_closed(self, fake_redis_cb):

        # seed
        pending = [{"transaction_id": "tx-recon-3"}, {"transaction_id": "tx-recon-4"}]

        with patch("apps.enrichment.documents.find_pending_older_than", return_value=pending):
            with patch("apps.enrichment.documents.update_status_if_not_terminal") as mock_update:
                with patch("apps.enrichment.tasks.enrich_transaction") as mock_task:

                    reconcile_pending()

                    assert mock_update.call_count == 2
                    mock_update.assert_any_call("tx-recon-3", "QUEUED")
                    mock_update.assert_any_call("tx-recon-4", "QUEUED")
                    assert mock_task.delay.call_count == 2
                    mock_task.delay.assert_any_call("tx-recon-3")
                    mock_task.delay.assert_any_call("tx-recon-4")
