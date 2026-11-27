"""
Tests for calendar calculations (Life Calendar 1.1).
Run: python -m pytest tests/ -q   or   python tests/test_calculations.py
"""

import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from calculations import (
    parse_date,
    calculate_life_stats,
    date_for_life_week,
    life_year_and_week_for_date,
    get_week_start,
)


def test_parse_date():
    assert parse_date("1990-05-15") == date(1990, 5, 15)
    assert parse_date("") is None
    assert parse_date("not-a-date") is None


def test_feb29_birth():
    """Leap-day birthday must not crash and must produce valid end date."""
    bd = date(2000, 2, 29)
    stats = calculate_life_stats(bd, life_expectancy=90, today=date(2026, 11, 27))
    assert stats["years"] == 26
    assert stats["end_date"].month == 2
    assert stats["end_date"].day in (28, 29)
    # date_for_life_week for year 0 week 0 should start near birth
    start, end = date_for_life_week(bd, 0, 0)
    assert start == bd or (start.month == 2 and start.day in (28, 29))


def test_age_boundary():
    """Age on birthday itself should increase correctly."""
    bd = date(2000, 1, 1)
    # Day before 26th birthday
    stats = calculate_life_stats(bd, 90, today=date(2025, 12, 31))
    assert stats["years"] == 25
    # On birthday
    stats2 = calculate_life_stats(bd, 90, today=date(2026, 1, 1))
    assert stats2["years"] == 26


def test_life_year_and_week():
    bd = date(1990, 6, 15)
    # Exactly 10 years later
    ly, w = life_year_and_week_for_date(date(2000, 6, 15), bd)
    assert ly == 10
    assert w == 0
    # A few weeks later
    ly2, w2 = life_year_and_week_for_date(date(2000, 7, 10), bd)
    assert ly2 == 10
    assert 0 <= w2 <= 51


def test_date_for_life_week_roundtrip():
    bd = date(1985, 3, 20)
    for year in (0, 5, 20, 40):
        for week in (0, 10, 25, 51):
            start, end = date_for_life_week(bd, year, week)
            assert (end - start).days == 6
            assert start <= end


def test_first_day_monday_default():
    """get_week_start with first_day=0 (Monday) should return Monday."""
    # 2026-11-27 is a Friday
    d = date(2026, 11, 27)
    start = get_week_start(d, first_day=0)
    assert start.weekday() == 0  # Monday
    # Sunday as first day
    start_sun = get_week_start(d, first_day=6)
    assert start_sun.weekday() == 6  # Sunday


def test_percent_and_remaining():
    bd = date(2000, 1, 1)
    stats = calculate_life_stats(bd, 90, today=date(2045, 1, 1))
    assert 45 <= stats["percent_lived"] <= 55
    assert stats["weeks_remaining"] > 0
    assert stats["days_lived"] > 0


if __name__ == "__main__":
    tests = [
        test_parse_date,
        test_feb29_birth,
        test_age_boundary,
        test_life_year_and_week,
        test_date_for_life_week_roundtrip,
        test_first_day_monday_default,
        test_percent_and_remaining,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  OK  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
