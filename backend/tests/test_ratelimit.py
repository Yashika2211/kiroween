from necromancer.ratelimit import RateLimiter


def test_sliding_window() -> None:
    now = [0.0]
    limiter = RateLimiter(limit=2, window_s=60, clock=lambda: now[0])
    assert limiter.check("a") is None
    assert limiter.check("a") is None
    wait = limiter.check("a")
    assert wait is not None and 59 <= wait <= 60
    assert limiter.check("b") is None  # keys are independent
    now[0] = 61
    assert limiter.check("a") is None


def test_zero_limit_disables() -> None:
    limiter = RateLimiter(limit=0, window_s=60)
    assert all(limiter.check("a") is None for _ in range(100))
