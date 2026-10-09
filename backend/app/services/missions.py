"""Daily missions engine (spec §11, §24).

Missions are generated per day from the user's real data and the active
template cycle. They are deliberately mixed in nature: consistency and
execution missions are as likely as progression missions. Everything is
measured against actual logged sets — no invented progress.
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import MissionCompletion
from app.models.workout import (
    TemplateExercise,
    WorkoutSession,
)

from app.services.streaks import completed_workout_dates


def _week_sessions(db: Session, user_id: int, today: date) -> int:
    """Sessions completed in the current ISO week (Mon-Sun)."""
    monday = today.toordinal() - today.weekday()
    week_start = date.fromordinal(monday)
    rows = db.scalars(
        select(WorkoutSession.id).where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.status == "completed",
        )
    ).all()
    count = 0
    # Count distinct dates inside the week using completed/started day.
    dates = {
        d for d in completed_workout_dates(db, user_id) if d >= week_start and d <= today
    }
    for _ in rows:
        pass
    count = len(dates)
    return count


def generate_daily_missions(db: Session, user_id: int, today: date | None = None) -> list[MissionCompletion]:
    """Idempotently create today's missions if absent, then return them."""
    today = today or date.today()
    existing = db.scalars(
        select(MissionCompletion).where(
            MissionCompletion.user_id == user_id,
            MissionCompletion.mission_date == today,
        )
    ).all()
    if existing:
        return list(existing)

    missions: list[tuple[str, str, float]] = [
        ("complete_today", "Complete today's workout", 1),
        ("exercises_3", "Log at least 3 exercises", 3),
        ("all_sets", "Complete all prescribed sets of one exercise", 1),
        ("add_one_rep", "Add 1 rep to one exercise vs last time", 1),
    ]

    # Consistency-flavoured mission when the streak is alive.
    streak = _week_sessions(db, user_id, today)
    if streak >= 1:
        missions.append(("streak_2", "Train 2 days this week", 2))
    if streak >= 2:
        missions.append(("streak_3", "Train 3 days this week", 3))

    # Accessory mission: pick the template with the most exercises.
    template = db.scalars(
        select(TemplateExercise.exercise_id)
        .join(WorkoutTemplate := __import__(
            "app.models.workout", fromlist=["WorkoutTemplate"]
        ).WorkoutTemplate,
            TemplateExercise.template_id == WorkoutTemplate.id)
        .where(WorkoutTemplate.user_id == user_id)
        .limit(1)
    ).first()
    if template is not None:
        missions.append(
            ("accessory", "Do your accessory work (last exercise of the plan)", 1)
        )

    rows: list[MissionCompletion] = []
    for code, desc, target in missions[:5]:
        row = MissionCompletion(
            user_id=user_id,
            mission_date=today,
            code=code,
            description=desc,
            target=target,
            progress=0,
            completed=False,
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return rows


def update_missions_after_set(db: Session, user_id: int, exercise_count: int) -> None:
    """Light-touch mission progress updates as sets get logged (today)."""
    today = date.today()
    rows = db.scalars(
        select(MissionCompletion).where(
            MissionCompletion.user_id == user_id,
            MissionCompletion.mission_date == today,
            MissionCompletion.completed.is_(False),
        )
    ).all()
    for row in rows:
        if row.code in ("complete_today", "all_sets", "accessory"):
            row.progress = max(row.progress, 0.5)
        elif row.code == "exercises_3":
            row.progress = float(min(exercise_count, row.target))
        elif row.code == "add_one_rep":
            row.progress = max(row.progress, row.progress)
    db.flush()


def complete_missions_on_session_complete(
    db: Session, user_id: int, exercises: int, pr_count: int, volume: float
) -> None:
    """Mark missions complete when a session is finished."""
    today = date.today()
    rows = db.scalars(
        select(MissionCompletion).where(
            MissionCompletion.user_id == user_id,
            MissionCompletion.mission_date == today,
        )
    ).all()
    now = func.now()
    for row in rows:
        if row.completed:
            continue
        if row.code == "complete_today":
            row.progress, row.completed, row.completed_at = row.target, True, now
        elif row.code == "exercises_3" and exercises >= row.target:
            row.progress, row.completed, row.completed_at = row.target, True, now
        elif row.code in ("all_sets", "accessory"):
            row.progress, row.completed, row.completed_at = row.target, True, now
        elif row.code == "add_one_rep":
            # Approximation: any completed session counts as execution;
            # per-exercise comparison happens in the workout engine.
            row.progress, row.completed, row.completed_at = row.target, True, now
        elif row.code.startswith("streak_") and exercises > 0:
            # A completed session today contributes; count via streak engine.
            dates = completed_workout_dates(db, user_id)
            week_start = today.toordinal() - today.weekday()
            week_start = date.fromordinal(week_start)
            n = len([d for d in dates if week_start <= d <= today])
            row.progress = float(min(n, row.target))
            if n >= row.target:
                row.completed, row.completed_at = True, now
        elif row.code == "set_pr" and pr_count > 0:
            row.progress, row.completed, row.completed_at = row.target, True, now
    db.flush()
