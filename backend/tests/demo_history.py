"""Test-only fictional training history (moved out of app.db.seed).

The dev database starts clean — no trial logs. Tests build their own
disposable history so engines and endpoints have meaningful data.
"""

from datetime import date, datetime, timedelta, timezone
import random

from sqlalchemy.orm import Session

from app.models import (
    BodyweightLog,
    User,
    WorkoutExercise,
    WorkoutSession,
    WorkoutSet,
)

rng = random.Random(42)


def _kind(resistance: str) -> str:
    return {
        "bodyweight": "bodyweight",
        "bodyweight_weighted": "bodyweight_weighted",
        "external": "weight",
        "duration": "duration",
    }[resistance]


def add_session(
    db: Session,
    user: User,
    catalog: dict[str, "Exercise"],
    day: date,
    name: str,
    entries: list[tuple[str, list[dict]]],
    started_at: datetime | None = None,
) -> WorkoutSession:
    started = started_at or datetime(
        day.year, day.month, day.day, 18, 0, tzinfo=timezone.utc
    )
    session = WorkoutSession(
        user_id=user.id, name=name, status="completed",
        started_at=started, completed_at=started + timedelta(minutes=65),
    )
    db.add(session)
    db.flush()
    for pos, (ex_name, sets) in enumerate(entries):
        ex = catalog[ex_name]
        we = WorkoutExercise(session_id=session.id, exercise_id=ex.id, position=pos)
        db.add(we)
        db.flush()
        kind = _kind(ex.resistance)
        for i, s in enumerate(sets):
            db.add(
                WorkoutSet(
                    workout_exercise_id=we.id,
                    exercise_kind=kind,
                    set_number=i + 1,
                    resistance_type=ex.resistance,
                    completed_at=started + timedelta(minutes=5 + i * 3),
                    **s,
                )
            )
    return session


def seed_demo_history(db: Session, user: User, catalog: dict[str, "Exercise"]) -> None:
    """5 weeks of fictional demo training (Mon Push, Wed Pull, Fri Legs)."""
    today = date.today()
    bench = [70.0, 72.5, 75.0, 77.5, 80.0]

    sessions: list[tuple[date, str, list[tuple[str, list[dict]]]]] = []

    for w in range(5):
        week_monday = today - timedelta(days=today.weekday()) - timedelta(weeks=4 - w)
        push_day = week_monday
        pull_day = week_monday + timedelta(days=2)
        leg_day = week_monday + timedelta(days=4)

        sessions.append((push_day, "Push", [
            ("Bench Press", [
                {"weight": bench[w], "reps": 8},
                {"weight": bench[w], "reps": 8},
                {"weight": bench[w], "reps": 7 if w < 4 else 8},
            ]),
            ("Incline Dumbbell Press", [
                {"weight": 20.0, "reps": 10, "per_dumbbell": True},
                {"weight": 20.0, "reps": 9, "per_dumbbell": True},
                {"weight": 22.5 if w >= 2 else 20.0, "reps": 8, "per_dumbbell": True},
            ]),
            ("Overhead Press", [
                {"weight": 40.0 + 2.5 * w, "reps": 6},
                {"weight": 40.0 + 2.5 * w, "reps": 5},
                {"weight": 37.5 + 2.5 * w, "reps": 7},
            ]),
            ("Lateral Raise", [
                {"weight": 8.0, "reps": 12, "per_dumbbell": True},
                {"weight": 8.0, "reps": 12, "per_dumbbell": True},
                {"weight": 8.0, "reps": 11, "per_dumbbell": True},
            ]),
            ("Triceps Pushdown", [
                {"weight": 30.0, "reps": 12},
                {"weight": 30.0, "reps": 12},
                {"weight": 30.0, "reps": 10},
            ]),
        ]))
        sessions.append((pull_day, "Pull", [
            ("Pull-Ups", [
                {"bodyweight": 78.0, "reps": 6 + w},
                {"bodyweight": 78.0, "reps": 6 + w},
                {"bodyweight": 78.0, "reps": 5 + w},
            ]),
            ("Lat Pulldown", [
                {"weight": 60.0 + 2.5 * (w // 2), "reps": 10},
                {"weight": 60.0 + 2.5 * (w // 2), "reps": 10},
                {"weight": 60.0 + 2.5 * (w // 2), "reps": 9},
            ]),
            ("Seated Cable Row", [
                {"weight": 55.0, "reps": 10},
                {"weight": 55.0, "reps": 10},
                {"weight": 55.0, "reps": 9},
            ]),
            ("Face Pull", [
                {"weight": 25.0, "reps": 15},
                {"weight": 25.0, "reps": 15},
                {"weight": 25.0, "reps": 14},
            ]),
            ("Barbell Curl", [
                {"weight": 30.0, "reps": 10},
                {"weight": 30.0, "reps": 9},
                {"weight": 27.5, "reps": 10},
            ]),
        ]))
        sessions.append((leg_day, "Legs", [
            ("Barbell Squat", [
                {"weight": 90.0 + 5 * w, "reps": 6},
                {"weight": 90.0 + 5 * w, "reps": 6},
                {"weight": 90.0 + 5 * w, "reps": 5 if w < 4 else 6},
            ]),
            ("Romanian Deadlift", [
                {"weight": 80.0 + 2.5 * w, "reps": 10},
                {"weight": 80.0 + 2.5 * w, "reps": 10},
                {"weight": 80.0 + 2.5 * w, "reps": 9},
            ]),
            ("Leg Press", [
                {"weight": 140.0 + 10 * w, "reps": 10},
                {"weight": 140.0 + 10 * w, "reps": 9},
                {"weight": 140.0 + 10 * w, "reps": 8},
            ]),
            ("Leg Curl", [
                {"weight": 45.0, "reps": 12},
                {"weight": 45.0, "reps": 11},
                {"weight": 45.0, "reps": 10},
            ]),
            ("Standing Calf Raise", [
                {"weight": 60.0, "reps": 15},
                {"weight": 60.0, "reps": 14},
                {"weight": 60.0, "reps": 12},
            ]),
        ]))

    for day, name, entries in sessions:
        add_session(db, user, catalog, day, name, entries)

    # Bodyweight log entries on training days.
    for i in range(35):
        d = today - timedelta(days=i)
        if d.weekday() in (0, 2, 4):
            db.add(BodyweightLog(user_id=user.id, log_date=d, weight_kg=78.0 + rng.uniform(-0.6, 0.6)))
