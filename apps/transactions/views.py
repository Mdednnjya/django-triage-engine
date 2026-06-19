from django.db import transaction as db_transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.transactions.models import Transaction
from apps.transactions.serializers import WebhookSerializer
from apps.transactions.services import TransactionService
from apps.enrichment import documents


FLAGGED = {"NEEDS_REVIEW", "AUTO_BLOCK"}


class WebhookView(APIView):

    def post(self, request):

        serializer = WebhookSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        service = TransactionService()
        transaction = service.process(
            tx_data=serializer.validated_data,
            idempotency_key=serializer.validated_data["idempotency_key"],
        )

        # enqueue
        if transaction.status in FLAGGED:
            from apps.enrichment.tasks import enrich_transaction
            with db_transaction.atomic():
                locked = Transaction.objects.select_for_update().get(id=transaction.id)
                if not locked.enrichment_queued:
                    enrich_transaction.delay(str(locked.id))
                    locked.enrichment_queued = True
                    locked.save(update_fields=["enrichment_queued"])
                    documents.save(
                        transaction_id=locked.id,
                        explanation=None,
                        status="QUEUED",
                        model=None,
                    )

        return Response(
            {
                "transaction_id": str(transaction.id),
                "status": transaction.status,
                "risk_score": transaction.risk_score,
                "reasons": transaction.reasons,
            },
            status=status.HTTP_202_ACCEPTED,
        )
