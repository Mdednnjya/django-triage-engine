import logging
from datetime import datetime, timedelta, timezone

from decouple import config

from config.celery import app
from apps.enrichment import circuit_breaker, documents

logger = logging.getLogger(__name__)


@app.task
def reconcile_pending():

    pending = documents.find_pending_older_than(
        cutoff=datetime.now(timezone.utc) - timedelta(
            minutes=int(config("RECONCILIATION_THRESHOLD_MINUTES", default=10))
        )
    )

    if not pending:
        logger.info("reconciliation: no pending enrichments found")
        return

    if not circuit_breaker.allow_request():
        logger.info("reconciliation: circuit open, skipping %d pending enrichments", len(pending))
        return

    from apps.enrichment.tasks import enrich_transaction

    for doc in pending:
        transaction_id = doc["transaction_id"]
        documents.update_status_if_not_terminal(transaction_id, "QUEUED")
        enrich_transaction.delay(transaction_id)

    logger.info("reconciliation: re-queued %d pending enrichments", len(pending))
