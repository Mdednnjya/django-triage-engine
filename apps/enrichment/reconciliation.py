import logging
import uuid
from datetime import datetime, timedelta, timezone

from decouple import config

from config.celery import app
from apps.enrichment import circuit_breaker, documents

logger = logging.getLogger(__name__)


@app.task
def reconcile_pending():

    from apps.core.logging import request_id_var

    token = request_id_var.set(str(uuid.uuid4()))

    try:
        pending = documents.find_pending_older_than(
            cutoff=datetime.now(timezone.utc) - timedelta(
                minutes=int(config("RECONCILIATION_THRESHOLD_MINUTES", default=10))
            )
        )

        if not pending:
            logger.info("reconciliation no pending")
            return

        if not circuit_breaker.allow_request():
            logger.info("reconciliation skipped", extra={"status": "OPEN", "count": len(pending)})
            return

        from apps.enrichment.tasks import enrich_transaction

        for doc in pending:
            transaction_id = doc["transaction_id"]
            documents.update_status_if_not_terminal(transaction_id, "QUEUED")
            enrich_transaction.delay(transaction_id)

        logger.info("reconciliation requeued", extra={"count": len(pending)})

    finally:
        request_id_var.reset(token)
