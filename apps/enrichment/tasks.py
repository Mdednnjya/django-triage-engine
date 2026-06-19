from config.celery import app
from apps.enrichment.services import EnrichmentService
from apps.enrichment import documents


@app.task(bind=True, max_retries=3)
def enrich_transaction(self, transaction_id):

    from apps.transactions.models import Transaction

    try:
        transaction = Transaction.objects.get(id=transaction_id)

        # call
        service = EnrichmentService()
        service.enrich(transaction)

    except Exception as exc:
        if self.request.retries >= self.max_retries:
            # exhausted
            documents.save(
                transaction_id=transaction_id,
                explanation=None,
                status="FAILED",
                model=None,
            )
        else:
            raise self.retry(exc=exc, countdown=60)
