"""
Lightweight tests for event-cache invalidation rules (no GUI).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def test_cache_key_and_clear():
    """Simulate the cache behaviour used in main.LifeCalendarApp."""
    cache = {}

    def get_cached(year, week, fetcher):
        key = (year, week)
        if key not in cache:
            cache[key] = fetcher(year, week)
        return cache[key]

    calls = []

    def fetcher(y, w):
        calls.append((y, w))
        return [{"title": f"e-{y}-{w}"}]

    # First access hits DB
    r1 = get_cached(10, 5, fetcher)
    assert r1[0]["title"] == "e-10-5"
    assert calls == [(10, 5)]

    # Second access uses cache
    r2 = get_cached(10, 5, fetcher)
    assert r2 is r1
    assert calls == [(10, 5)]

    # After mutation we clear
    cache.clear()
    r3 = get_cached(10, 5, fetcher)
    assert calls == [(10, 5), (10, 5)]
    assert r3[0]["title"] == "e-10-5"


if __name__ == "__main__":
    test_cache_key_and_clear()
    print("  OK  test_cache_key_and_clear")
    print("\n1 passed, 0 failed")
