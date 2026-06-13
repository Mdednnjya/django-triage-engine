from dataclasses import dataclass, field


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

        return RuleResult(triggered=False, reason="", weight=0)


class FrequencyRule:

    def evaluate(self, tx_data):

        return RuleResult(triggered=False, reason="", weight=0)


class GeoMismatchRule:

    def evaluate(self, tx_data):

        return RuleResult(triggered=False, reason="", weight=0)


class RuleEngine:

    def __init__(self):
        self.rules = []

    def evaluate(self, tx_data):

        return RiskVerdict(status="AUTO_APPROVE", score=0, reasons=[])
