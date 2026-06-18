from config.celery import app
from apps.enrichment.services import EnrichmentService


@app.task(bind=True, max_retries=3)
def enrich_transaction(self, transaction_id):

    from apps.transactions.models import Transaction

    try:
        transaction = Transaction.objects.get(id=transaction_id)

        # call
        service = EnrichmentService()
        service.enrich(transaction)

    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
