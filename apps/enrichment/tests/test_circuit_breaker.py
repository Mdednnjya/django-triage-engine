import time

import fakeredis
import pytest
from unittest.mock import patch

import apps.enrichment.circuit_breaker as cb


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    server = fakeredis.FakeServer()
    r = fakeredis.FakeRedis(server=server)
    monkeypatch.setattr(cb, "_r", lambda: r)
    yield r
    r.flushall()


class TestCircuitBreaker:

    def test_allows_request_with_no_state(self, fake_redis):

        assert cb.allow_request() is True

    def test_opens_after_threshold_failures(self, fake_redis):

        threshold = cb._threshold()
        for _ in range(threshold):
            cb.record_failure()

        assert cb.allow_request() is False

    def test_does_not_open_before_threshold(self, fake_redis):

        threshold = cb._threshold()
        for _ in range(threshold - 1):
            cb.record_failure()

        assert cb.allow_request() is True

    def test_blocks_request_when_open_within_cooldown(self, fake_redis):

        # seed
        fake_redis.hset(cb._KEY, mapping={
            "state": "OPEN",
            "failure_count": 3,
            "last_failure_at": str(time.time()),
        })

        assert cb.allow_request() is False

    def test_allows_single_trial_when_cooldown_expired(self, fake_redis):

        # seed
        fake_redis.hset(cb._KEY, mapping={
            "state": "OPEN",
            "failure_count": 3,
            "last_failure_at": str(time.time() - cb._cooldown() - 1),
        })

        assert cb.allow_request() is True

    def test_only_one_trial_in_half_open(self, fake_redis):

        # seed
        fake_redis.hset(cb._KEY, mapping={
            "state": "OPEN",
            "failure_count": 3,
            "last_failure_at": str(time.time() - cb._cooldown() - 1),
        })

        first = cb.allow_request()
        second = cb.allow_request()

        assert first is True
        assert second is False

    def test_closes_after_trial_success(self, fake_redis):

        # seed
        fake_redis.hset(cb._KEY, mapping={
            "state": "OPEN",
            "failure_count": 3,
            "last_failure_at": str(time.time() - cb._cooldown() - 1),
        })

        # claim trial
        cb.allow_request()

        cb.record_success()

        assert cb.allow_request() is True
        count = fake_redis.hget(cb._KEY, "failure_count")
        assert int(count) == 0

    def test_reopens_after_trial_failure(self, fake_redis):

        # seed
        past = str(time.time() - cb._cooldown() - 1)
        fake_redis.hset(cb._KEY, mapping={
            "state": "OPEN",
            "failure_count": 3,
            "last_failure_at": past,
        })
        
        # claim trial
        cb.allow_request()
        before = float(fake_redis.hget(cb._KEY, "last_failure_at"))

        cb.record_failure()

        assert cb.allow_request() is False
        count = int(fake_redis.hget(cb._KEY, "failure_count"))
        after = float(fake_redis.hget(cb._KEY, "last_failure_at"))
        assert count == 1
        assert after > before

    def test_fails_open_when_redis_unavailable(self, monkeypatch):

        def boom():
            raise ConnectionError("redis down")
        monkeypatch.setattr(cb, "_r", boom)

        assert cb.allow_request() is True
