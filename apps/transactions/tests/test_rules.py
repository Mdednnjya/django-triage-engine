import pytest
from apps.transactions.rules import AmountRule, FrequencyRule, GeoMismatchRule, RuleEngine


class TestAmountRule:

    def test_triggers_above_threshold(self):

        rule = AmountRule()
        result = rule.evaluate({"amount": 51_000_000})
        assert result.triggered is True
        assert result.weight == 60

    def test_no_trigger_at_threshold(self):

        rule = AmountRule()
        result = rule.evaluate({"amount": 50_000_000})
        assert result.triggered is False
        assert result.weight == 0

    def test_no_trigger_below_threshold(self):

        rule = AmountRule()
        result = rule.evaluate({"amount": 10_000_000})
        assert result.triggered is False

    def test_missing_amount_defaults_safe(self):

        rule = AmountRule()
        result = rule.evaluate({})
        assert result.triggered is False


class TestFrequencyRule:

    @pytest.mark.django_db
    def test_no_trigger_below_limit(self):

        rule = FrequencyRule()
        result = rule.evaluate({"user_id": "user-1"})
        assert result.triggered is False

    @pytest.mark.django_db
    def test_triggers_above_limit(self):

        from apps.transactions.models import Transaction

        for i in range(6):
            Transaction.objects.create(
                amount=10_000,
                currency="IDR",
                user_id="user-freq",
                merchant_name="merchant",
                status="AUTO_APPROVE",
                risk_score=0,
                reasons=[],
                idempotency_key=f"freq-key-{i}",
            )

        rule = FrequencyRule()
        result = rule.evaluate({"user_id": "user-freq"})
        assert result.triggered is True
        assert result.weight == 40

    def test_no_trigger_missing_user_id(self):

        rule = FrequencyRule()
        result = rule.evaluate({})
        assert result.triggered is False


class TestGeoMismatchRule:

    def test_triggers_on_mismatch(self):

        rule = GeoMismatchRule()
        result = rule.evaluate({"location": "Jakarta", "user_location": "Surabaya"})
        assert result.triggered is True
        assert result.weight == 30

    def test_no_trigger_on_match(self):

        rule = GeoMismatchRule()
        result = rule.evaluate({"location": "Jakarta", "user_location": "Jakarta"})
        assert result.triggered is False

    def test_no_trigger_missing_location(self):

        rule = GeoMismatchRule()
        result = rule.evaluate({"user_location": "Jakarta"})
        assert result.triggered is False

    def test_no_trigger_missing_user_location(self):

        rule = GeoMismatchRule()
        result = rule.evaluate({"location": "Jakarta"})
        assert result.triggered is False

    def test_case_insensitive_match(self):

        rule = GeoMismatchRule()
        result = rule.evaluate({"location": "jakarta", "user_location": "Jakarta"})
        assert result.triggered is False


class TestRuleEngine:

    def test_auto_block_on_high_score(self):

        engine = RuleEngine()
        result = engine.evaluate({"amount": 60_000_000})
        assert result.status == "AUTO_BLOCK"
        assert result.score >= 60

    def test_auto_approve_on_clean_tx(self):

        engine = RuleEngine()
        result = engine.evaluate({"amount": 10_000, "user_id": "user-x"})
        assert result.status == "AUTO_APPROVE"
