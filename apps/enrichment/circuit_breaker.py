import logging
import time

import redis as redis_lib
from decouple import config

logger = logging.getLogger(__name__)


_KEY = "circuit_breaker:llm"
_TRIAL_KEY = "circuit_breaker:llm:trial"


def _r():
    return redis_lib.from_url(config("REDIS_URL", default="redis://localhost:6379/0"))


def _threshold():
    return int(config("CIRCUIT_BREAKER_THRESHOLD", default=3))


def _cooldown():
    return int(config("CIRCUIT_BREAKER_COOLDOWN", default=60))


def allow_request():

    try:
        r = _r()
        data = r.hgetall(_KEY)

        if not data:
            return True

        s = data.get(b"state", b"CLOSED").decode()

        if s == "CLOSED":
            return True

        # cooldown expired: attempt trial
        last_at = float(data.get(b"last_failure_at", 0))
        if time.time() - last_at < _cooldown():
            return False

        # trial
        acquired = r.set(_TRIAL_KEY, "1", nx=True, ex=_cooldown())
        return bool(acquired)

    except Exception:
        logger.warning("circuit breaker: redis unavailable, failing open")
        return True


def record_success():

    r = _r()
    # reset
    pipe = r.pipeline()
    pipe.hset(_KEY, mapping={"state": "CLOSED", "failure_count": 0})
    pipe.delete(_TRIAL_KEY)
    pipe.execute()


def record_failure():

    r = _r()
    data = r.hgetall(_KEY)
    s = data.get(b"state", b"CLOSED").decode() if data else "CLOSED"

    if s == "OPEN":

        # reopen
        pipe = r.pipeline()
        pipe.hset(_KEY, mapping={
            "state": "OPEN",
            "failure_count": 1,
            "last_failure_at": str(time.time()),
        })
        pipe.delete(_TRIAL_KEY)
        pipe.execute()
        return

    # increment
    new_count = int(r.hincrby(_KEY, "failure_count", 1))
    if new_count >= _threshold():
        # open
        r.hset(_KEY, mapping={
            "state": "OPEN",
            "last_failure_at": str(time.time()),
        })
