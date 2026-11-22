from app.security import RateLimiter


def test_limiter_blocks_over_limit_and_isolates_keys():
    limiter = RateLimiter(2, 60)
    assert [limiter.allow("a") for _ in range(3)] == [True, True, False]
    assert limiter.allow("b") is True


def test_limiter_window_expires(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("app.security.time.monotonic", lambda: now[0])
    limiter = RateLimiter(1, 10)
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False
    now[0] += 11
    assert limiter.allow("a") is True


def test_limiter_drops_idle_keys(monkeypatch):
    now = [0.0]
    monkeypatch.setattr("app.security.time.monotonic", lambda: now[0])
    limiter = RateLimiter(5, 10)
    limiter.allow("old")
    now[0] += 30
    limiter.allow("new")
    assert list(limiter._hits) == ["new"]
