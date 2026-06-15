from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.transactions.serializers import WebhookSerializer
from apps.transactions.services import TransactionService


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

        return Response(
            {
                "transaction_id": str(transaction.id),
                "status": transaction.status,
                "risk_score": transaction.risk_score,
                "reasons": transaction.reasons,
            },
            status=status.HTTP_200_OK,
        )
