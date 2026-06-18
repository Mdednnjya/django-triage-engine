from datetime import datetime, timezone

from django.conf import settings
from pymongo import MongoClient


def _collection():

    client = MongoClient(settings.MONGO_URI)
    return client[settings.MONGO_DB]["enrichments"]


def save(transaction_id, explanation, status, model):

    _collection().insert_one({
        "transaction_id": str(transaction_id),
        "explanation": explanation,
        "enrichment_status": status,
        "model": model,
        "created_at": datetime.now(timezone.utc),
    })


def find_by_transaction_ids(transaction_ids):

    ids = [str(tid) for tid in transaction_ids]
    return {
        doc["transaction_id"]: doc
        for doc in _collection().find({"transaction_id": {"$in": ids}})
    }
