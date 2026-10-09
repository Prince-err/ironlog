"""Streak engine (spec §10).

A streak counts completed workout days — opening the app does nothing.
Rest days do not break a streak: only a gap of 2+ consecutive non-training
days does. Streak state is a cache; sessions are the source of truth.
"""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import StreakState
from app.models.workout import WorkoutSession


def completed_workout_dates(db: Session, user_id: int) -> list[date]:
    """Distinct completed workout dates (UTC day of completed_at/started_at)."""
    rows = db.execute(
        select(func.date(func.coalesce(WorkoutSession.completed_at, WorkoutSession.started_at)))
        .where(WorkoutSession.user_id == user_id, WorkoutSession.status == "completed")
        .distinct()
        .order_by(func.date(func.coalesce(WorkoutSession.completed_at, WorkoutSession.started_at)))
    ).all()
    out: list[date] = []
    for (d,) in rows:
        if isinstance(d, str):
            d = date.fromisoformat(d[:10])
        elif not isinstance(d, date):
            d = d.date() if hasattr(d, "date") else d
        out.append(d)
    return out


def compute_streak(db: Session, user_id: int, today: date | None = None) -> dict:
    """Return streak info: current, longest, last date, worked out today."""
    today = today or date.today()
    dates = set(completed_workout_dates(db, user_id))
    if not dates:
        return {"current_streak": 0, "longest_streak": 0,
                "last_workout_date": None, "worked_out_today": False}

    last = max(dates)

    # Current streak: count consecutive WORKOUT days starting from the most
    # recent one, tolerating ONE rest day between workouts (a 2+ day gap
    # breaks the chain). The streak is "live" only if the last workout was
    # today or yesterday; opening the app without training changes nothing.
    current = 0
    if (today - last).days <= 2:
        chain = [last]
        for d in sorted(dates, reverse=True):
            if d == last:
                continue
            if (chain[-1] - d).days <= 2:  # at most one rest day between
                chain.append(d)
            else:
                break
        current = len(chain)

    # Longest streak across all history.
    ordered = sorted(dates)
    longest = 1
    run = 1
    for prev, cur in zip(ordered, ordered[1:]):
        if (cur - prev).days <= 2:  # rest day tolerated
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    return {
        "current_streak": current,
        "longest_streak": longest,
        "last_workout_date": last.isoformat(),
        "worked_out_today": today in dates,
    }


def refresh_streak_state(db: Session, user_id: int, today: date | None = None) -> dict:
    """Recompute and persist the cached streak state; return it."""
    info = compute_streak(db, user_id, today)
    row = db.scalar(select(StreakState).where(StreakState.user_id == user_id))
    if row is None:
        row = StreakState(user_id=user_id)
        db.add(row)
    row.current_streak = info["current_streak"]
    row.longest_streak = info["longest_streak"]
    row.last_workout_date = (
        date.fromisoformat(info["last_workout_date"])
        if info["last_workout_date"]
        else None
    )
    db.flush()
    return info
