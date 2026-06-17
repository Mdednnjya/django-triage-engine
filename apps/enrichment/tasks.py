from config.celery import app


@app.task(bind=True, max_retries=3)
def enrich_transaction(self, transaction_id):
    pass
