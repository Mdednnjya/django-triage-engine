from dataclasses import dataclass, field
from datetime import timedelta

from django.utils import timezone


@dataclass
class RuleResult:

    triggered: bool
    reason: str
    weight: int


@dataclass
class RiskVerdict:

    status: str
    score: int
    reasons: list = field(default_factory=list)


class AmountRule:

    def evaluate(self, tx_data):

        amount = tx_data.get("amount", 0)

        # checker
        if amount > 50_000_000:
            return RuleResult(triggered=True, reason="amount exceeds threshold", weight=60)

        return RuleResult(triggered=False, reason="", weight=0)


class FrequencyRule:

    def evaluate(self, tx_data):

        from apps.transactions.models import Transaction

        user_id = tx_data.get("user_id")
        if not user_id:
            return RuleResult(triggered=False, reason="", weight=0)

        window = timezone.now() - timedelta(minutes=10)
        count = Transaction.objects.filter(
            user_id=user_id,
            created_at__gte=window,
        ).count()

        # checker
        if count > 5:
            return RuleResult(triggered=True, reason="frequency exceeds limit", weight=40)

        return RuleResult(triggered=False, reason="", weight=0)


class GeoMismatchRule:

    def evaluate(self, tx_data):

        location = tx_data.get("location", "")
        user_location = tx_data.get("user_location", "")

        if not location or not user_location:
            return RuleResult(triggered=False, reason="", weight=0)

        # checker
        if location.strip().lower() != user_location.strip().lower():
            return RuleResult(triggered=True, reason="location mismatch", weight=30)

        return RuleResult(triggered=False, reason="", weight=0)


class RuleEngine:

    def __init__(self):
        self.rules = [AmountRule(), FrequencyRule(), GeoMismatchRule()]

    def evaluate(self, tx_data):

        results = [rule.evaluate(tx_data) for rule in self.rules]
        score = sum(r.weight for r in results if r.triggered)
        reasons = [r.reason for r in results if r.triggered]

        # verdict
        if score >= 60:
            return RiskVerdict(status="AUTO_BLOCK", score=score, reasons=reasons)

        if score >= 30:
            return RiskVerdict(status="NEEDS_REVIEW", score=score, reasons=reasons)

        return RiskVerdict(status="AUTO_APPROVE", score=score, reasons=reasons)
