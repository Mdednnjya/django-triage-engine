import logging

from config.celery import app
from apps.enrichment.services import EnrichmentService
from apps.enrichment import documents

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3)
def enrich_transaction(self, transaction_id, request_id="-"):

    from apps.transactions.models import Transaction
    from apps.core.logging import request_id_var

    # propagate
    token = request_id_var.set(request_id)

    try:
        transaction = Transaction.objects.get(id=transaction_id)

        logger.info("enrichment started", extra={"transaction_id": transaction_id, "status": "PROCESSING"})

        # processing
        documents.update(transaction_id, "PROCESSING")

        service = EnrichmentService()
        service.enrich(transaction)

    except Exception as exc:

        if self.request.retries >= self.max_retries:

            from apps.core.metrics import enrichment_status_total
            
            # exhausted
            enrichment_status_total.labels(status="FAILED").inc()
            logger.info("enrichment failed", extra={"transaction_id": transaction_id, "status": "FAILED"})
            documents.update(transaction_id, "FAILED")

        else:
            raise self.retry(exc=exc, countdown=60)

    finally:
        # cleanup
        request_id_var.reset(token)
