from config.celery import app
from apps.enrichment.services import EnrichmentService
from apps.enrichment import documents


@app.task(bind=True, max_retries=3)
def enrich_transaction(self, transaction_id):

    from apps.transactions.models import Transaction

    try:
        transaction = Transaction.objects.get(id=transaction_id)

        # processing
        documents.update(transaction_id, "PROCESSING")

        service = EnrichmentService()
        service.enrich(transaction)

    except Exception as exc:

        if self.request.retries >= self.max_retries:
            # exhausted
            documents.update(transaction_id, "FAILED")
            
        else:
            raise self.retry(exc=exc, countdown=60)
