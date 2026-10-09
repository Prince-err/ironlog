"""Analytics engine (spec §16, §17, §24).

All numbers derive from completed sessions' sets. No invented progress;
estimated metrics are labelled as estimates by the API layer.
"""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.exercise import Exercise
from app.models.reference import MuscleGroup
from app.models.workout import (
    WorkoutExercise,
    WorkoutSession,
    WorkoutSet,
)

from app.services.metrics import effective_load, set_volume
from app.services.streaks import completed_workout_dates


def _completed_sets(
    db: Session, user_id: int, since: date | None = None
) -> list[tuple[WorkoutSession, WorkoutExercise, WorkoutSet]]:
    q = (
        select(WorkoutSession, WorkoutExercise, WorkoutSet)
        .join(WorkoutExercise, WorkoutExercise.session_id == WorkoutSession.id)
        .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
        .where(WorkoutSession.user_id == user_id, WorkoutSession.status == "completed")
        .order_by(WorkoutSession.started_at)
    )
    if since:
        q = q.where(WorkoutSession.started_at >= since)
    return db.execute(q).all()


def period_start(range_key: str, today: date | None = None) -> date | None:
    today = today or date.today()
    return {
        "7d": today - timedelta(days=7),
        "30d": today - timedelta(days=30),
        "3m": today - timedelta(days=91),
        "6m": today - timedelta(days=182),
        "1y": today - timedelta(days=365),
    }.get(range_key)  # "all" -> None


def volume_summary(db: Session, user_id: int, range_key: str = "30d") -> dict:
    today = date.today()
    start = period_start(range_key, today)
    rows = _completed_sets(db, user_id, start)

    sessions = {s.id: s for s, _, _ in rows}
    total_volume = 0.0
    total_reps = 0
    total_sets = 0
    for s, _, st in rows:
        v = set_volume(st)
        total_volume += v
        total_sets += 1
        total_reps += st.reps or 0

    durations = []
    for s in sessions.values():
        end = s.completed_at or s.started_at
        if s.started_at and end:
            durations.append((end - s.started_at).total_seconds() / 60)

    return {
        "range": range_key,
        "total_volume": round(total_volume, 1),
        "total_reps": total_reps,
        "total_sets": total_sets,
        "sessions": len(sessions),
        "avg_session_minutes": round(sum(durations) / len(durations), 1) if durations else 0,
    }


def muscle_group_volume(db: Session, user_id: int, range_key: str = "30d") -> list[dict]:
    """Approximate training volume by primary muscle group (spec §17)."""
    start = period_start(range_key)
    rows = _completed_sets(db, user_id, start)
    out: dict[str, float] = {}
    for _, we, st in rows:
        vol = set_volume(st)
        if vol <= 0:
            continue
        ex = we.exercise
        if ex is None:
            continue
        primary = next(
            (m for m in ex.muscles if m.is_primary), None
        )
        if primary is None:
            continue
        mg = db.get(MuscleGroup, primary.muscle_group_id)
        if mg is None:
            continue
        out[mg.name] = out.get(mg.name, 0.0) + vol
    total = sum(out.values())
    return [
        {
            "muscle_group": name,
            "volume": round(v, 1),
            "share": round(100 * v / total, 1) if total else 0.0,
        }
        for name, v in sorted(out.items(), key=lambda kv: -kv[1])
    ]


def heatmap(db: Session, user_id: int, days: int = 182) -> list[dict]:
    """GitHub-style training heatmap: completed sessions per day."""
    today = date.today()
    start = today - timedelta(days=days)
    dates = [d for d in completed_workout_dates(db, user_id) if d >= start]
    counts: dict[date, int] = {}
    for d in dates:
        counts[d] = counts.get(d, 0) + 1
    out = []
    for i in range(days, -1, -1):
        d = today - timedelta(days=i)
        out.append({"date": d.isoformat(), "workouts": counts.get(d, 0)})
    return out


def smart_recommendations(db: Session, user_id: int, today: date | None = None) -> list[str]:
    """Data-grounded insights (spec §24). Only claims what the data shows."""
    today = today or date.today()
    recs: list[str] = []

    # Training frequency this week.
    week_start = date.fromordinal(today.toordinal() - today.weekday())
    dates = completed_workout_dates(db, user_id)
    week_n = len([d for d in dates if d >= week_start])
    if week_n:
        recs.append(f"You have completed {week_n} workout{'s' if week_n != 1 else ''} this week.")

    # Muscle group recency (7+ days untouched).
    rows = _completed_sets(db, user_id, today - timedelta(days=60))
    last_by_group: dict[str, date] = {}
    for s, we, _ in rows:
        d = s.started_at.date()
        ex = we.exercise
        if ex is None:
            continue
        primary = next((m for m in ex.muscles if m.is_primary), None)
        if primary is None:
            continue
        mg = db.get(MuscleGroup, primary.muscle_group_id)
        if mg is None:
            continue
        if mg.name not in last_by_group or d > last_by_group[mg.name]:
            last_by_group[mg.name] = d
    for name, d in sorted(last_by_group.items(), key=lambda kv: kv[1]):
        gap = (today - d).days
        if gap >= 7:
            recs.append(f"You haven't trained {name} in {gap} days.")

    # Load progression trend per big lift (6 weeks).
    strength = strength_progression(db, user_id, weeks=6)
    for item in strength[:3]:
        if item["change_weight"] and item["change_weight"] > 0:
            recs.append(
                f"You increased your {item['exercise']} by "
                f"{item['change_weight']:g} kg over the last 6 weeks."
            )
        elif item["first_top_reps"] and item["last_top_reps"] and item["last_top_reps"] > item["first_top_reps"]:
            recs.append(
                f"Your {item['exercise']} reps increased from "
                f"{item['first_top_reps']} to {item['last_top_reps']}."
            )

    return recs[:6]


def strength_progression(db: Session, user_id: int, weeks: int = 6) -> list[dict]:
    """Per exercise: top weight first vs last within the window."""
    start = date.today() - timedelta(weeks=weeks)
    rows = _completed_sets(db, user_id, start)
    per_ex: dict[int, list[tuple[date, float, int | None]]] = {}
    ex_names: dict[int, str] = {}
    for s, we, st in rows:
        load = effective_load(st)
        if load is None or st.reps is None:
            continue
        per_ex.setdefault(we.exercise_id, []).append(
            (s.started_at.date(), load, st.reps)
        )
        ex_names[we.exercise_id] = we.exercise.name

    out = []
    for ex_id, entries in per_ex.items():
        entries.sort()
        first, last = entries[0], entries[-1]
        out.append(
            {
                "exercise_id": ex_id,
                "exercise": ex_names[ex_id],
                "first_top_weight": first[1],
                "last_top_weight": last[1],
                "change_weight": round(last[1] - first[1], 2),
                "first_top_reps": first[2],
                "last_top_reps": last[2],
            }
        )
    return sorted(out, key=lambda x: -abs(x["change_weight"]))
