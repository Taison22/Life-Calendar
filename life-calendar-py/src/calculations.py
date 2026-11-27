"""
Life Calendar - Date and age calculations.
Accurate calendar math with leap years.
"""

from datetime import date, datetime, timedelta
from typing import Tuple, Optional, Dict, Any
import calendar


def parse_date(s: str) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def get_iso_week(d: date) -> Tuple[int, int]:
    """Return (iso_year, iso_week) for a date. ISO weeks start on Monday."""
    return d.isocalendar()[:2]


def weeks_between(start: date, end: date) -> int:
    """Approximate full weeks between two dates."""
    return (end - start).days // 7


def get_week_start(d: date, first_day: int = 0) -> date:
    """
    first_day: 0=Monday ... 6=Sunday (ISO style for 0).
    Returns the start of the week containing d.
    """
    # Python weekday: Mon=0 ... Sun=6
    wd = d.weekday()
    delta = (wd - first_day) % 7
    return d - timedelta(days=delta)


def get_week_dates(year: int, week: int, first_day: int = 0) -> Tuple[date, date]:
    """Return (start, end) dates for ISO-like week of the given year/week."""
    # Use ISO year/week for consistency
    # First day of ISO week 1
    jan4 = date(year, 1, 4)
    start_of_week1 = get_week_start(jan4, 0)  # ISO is Monday
    start = start_of_week1 + timedelta(weeks=week - 1)
    end = start + timedelta(days=6)
    return start, end


def calculate_life_stats(
    birth_date: date,
    life_expectancy: int = 90,
    today: Optional[date] = None,
    first_day_of_week: int = 0,
) -> Dict[str, Any]:
    if today is None:
        today = date.today()

    if birth_date > today:
        birth_date = today

    # Age in years, months, days roughly
    years = today.year - birth_date.year
    months = today.month - birth_date.month
    days = today.day - birth_date.day
    if days < 0:
        months -= 1
        days += calendar.monthrange(today.year, today.month - 1 if today.month > 1 else 12)[1]
    if months < 0:
        years -= 1
        months += 12

    # Precise days lived
    days_lived = (today - birth_date).days
    weeks_lived = days_lived // 7

    # Expected end date
    try:
        end_date = birth_date.replace(year=birth_date.year + life_expectancy)
    except ValueError:
        # Feb 29
        end_date = birth_date.replace(year=birth_date.year + life_expectancy, day=28)

    days_remaining = max(0, (end_date - today).days)
    weeks_remaining = days_remaining // 7
    total_weeks = life_expectancy * 52  # approximate, ignore leap for total
    # Better total weeks
    total_days = (end_date - birth_date).days
    total_weeks_precise = total_days // 7

    percent_lived = min(100.0, (days_lived / max(1, total_days)) * 100)

    # Current week of life
    current_iso_year, current_iso_week = get_iso_week(today)
    birth_iso_year, birth_iso_week = get_iso_week(birth_date)

    # Age in weeks more precisely
    weeks_from_birth = weeks_between(birth_date, today)

    # Next birthday
    try:
        next_bday = birth_date.replace(year=today.year)
        if next_bday <= today:
            next_bday = birth_date.replace(year=today.year + 1)
    except ValueError:
        next_bday = date(today.year + (0 if today.month < 2 or (today.month == 2 and today.day < 29) else 1), 2, 28)

    days_to_next_bday = (next_bday - today).days
    weeks_to_next_bday = days_to_next_bday // 7

    # Time since last birthday
    try:
        last_bday = birth_date.replace(year=today.year)
        if last_bday > today:
            last_bday = birth_date.replace(year=today.year - 1)
    except ValueError:
        last_bday = date(today.year - 1, 2, 28)
    days_since_last = (today - last_bday).days

    # Current age year and week-of-year for grid
    # We map life year 0 = birth year weeks
    life_year = years  # completed years
    # Week within current life year: approximate from birthday
    days_into_year = (today - last_bday).days
    week_of_life_year = min(51, days_into_year // 7)

    return {
        "birth_date": birth_date,
        "today": today,
        "years": years,
        "months": months,
        "days": days,
        "days_lived": days_lived,
        "weeks_lived": weeks_lived,
        "days_remaining": days_remaining,
        "weeks_remaining": weeks_remaining,
        "total_weeks": total_weeks_precise,
        "percent_lived": round(percent_lived, 2),
        "life_expectancy": life_expectancy,
        "end_date": end_date,
        "current_iso_year": current_iso_year,
        "current_iso_week": current_iso_week,
        "life_year": life_year,
        "week_of_life_year": week_of_life_year,
        "days_to_next_birthday": days_to_next_bday,
        "weeks_to_next_birthday": weeks_to_next_bday,
        "days_since_last_birthday": days_since_last,
        "next_birthday": next_bday,
        "last_birthday": last_bday,
    }


def life_year_and_week_for_date(
    target: date,
    birth_date: date,
) -> Tuple[int, int]:
    """
    Map a calendar date to (life_year 0..N, week_in_year 0..51).
    life_year 0 starts at birth.
    """
    if target < birth_date:
        return 0, 0
    days = (target - birth_date).days
    life_year = days // 365  # approximate; better use birthday anniversary
    # More accurate: count full years via birthdays
    years = target.year - birth_date.year
    try:
        anniversary = birth_date.replace(year=target.year)
    except ValueError:
        anniversary = date(target.year, 2, 28)
    if anniversary > target:
        years -= 1
        try:
            anniversary = birth_date.replace(year=target.year - 1)
        except ValueError:
            anniversary = date(target.year - 1, 2, 28)
    days_into = (target - anniversary).days
    week = min(51, days_into // 7)
    return years, week


def date_for_life_week(
    birth_date: date,
    life_year: int,
    week_in_year: int,
) -> Tuple[date, date]:
    """Return (start, end) of the week corresponding to life_year / week_in_year."""
    try:
        anniversary = birth_date.replace(year=birth_date.year + life_year)
    except ValueError:
        anniversary = date(birth_date.year + life_year, 2, 28)
    start = anniversary + timedelta(weeks=week_in_year)
    end = start + timedelta(days=6)
    return start, end
