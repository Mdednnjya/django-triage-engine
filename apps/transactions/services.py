from apps.transactions.models import Transaction
from apps.transactions.rules import RuleEngine


class TransactionService:

    def __init__(self):
        self.rule_engine = RuleEngine()

    def process(self, tx_data, idempotency_key):

        # screen
        verdict = self.rule_engine.evaluate(tx_data)

        transaction = Transaction.objects.create(
            amount=tx_data["amount"],
            currency=tx_data["currency"],
            user_id=tx_data["user_id"],
            merchant_name=tx_data["merchant_name"],
            description=tx_data.get("description", ""),
            memo=tx_data.get("memo", ""),
            location=tx_data.get("location", ""),
            status=verdict.status,
            risk_score=verdict.score,
            reasons=verdict.reasons,
            idempotency_key=idempotency_key,
        )

        return transaction
