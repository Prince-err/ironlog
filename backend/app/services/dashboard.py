"""Dashboard service (spec §9, §22): everything the home screen needs in one
call — streak, today's plan/progress, mission, next overload target, recent
PRs."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import MissionCompletion, PersonalRecord
from app.models.workout import (
    WorkoutExercise,
    WorkoutSession,
    WorkoutSet,
    WorkoutTemplate,
)

from app.services import missions as missions_service
from app.services import streaks as streaks_service
from app.services.analytics import smart_recommendations
from app.services.overload import recommend


def dashboard(db: Session, user_id: int, today: date | None = None) -> dict:
    today = today or date.today()
    hour = datetime.now().hour

    # ---- streak ----
    streak = streaks_service.compute_streak(db, user_id, today)

    # ---- active / today's session ----
    active = db.scalars(
        select(WorkoutSession)
        .where(WorkoutSession.user_id == user_id, WorkoutSession.status == "in_progress")
        .order_by(WorkoutSession.started_at.desc())
        .limit(1)
    ).first()

    todays = None
    if active and active.started_at.date() == today:
        done_ex = sum(1 for we in active.exercises if any(s.reps or s.duration for s in we.sets))
        todays = {
            "session_id": active.id,
            "name": active.name,
            "progress_exercises_done": done_ex,
            "progress_exercises_total": len(active.exercises),
        }

    # ---- daily mission ----
    missions = missions_service.generate_daily_missions(db, user_id, today)
    primary = next((m for m in missions if not m.completed), missions[0] if missions else None)
    mission = (
        {
            "code": primary.code,
            "description": primary.description,
            "progress": primary.progress,
            "target": primary.target,
            "completed": primary.completed,
        }
        if primary
        else None
    )

    # ---- next overload target (most recent exercise in the rotation) ----
    next_target = None
    last_exercise_rows = db.execute(
        select(WorkoutSet, WorkoutExercise, WorkoutSession)
        .join(WorkoutExercise, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
        .join(WorkoutSession, WorkoutExercise.session_id == WorkoutSession.id)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.status == "completed",
        )
        .order_by(WorkoutSession.started_at.desc(), WorkoutSet.set_number)
        .limit(40)
    ).all()
    per_ex_sets: dict[int, list[WorkoutSet]] = {}
    ex_names: dict[int, str] = {}
    for s, we, sess in last_exercise_rows:
        per_ex_sets.setdefault(we.exercise_id, []).append(s)
        ex_names.setdefault(we.exercise_id, we.exercise.name)
    if per_ex_sets:
        # pick the exercise from the most recent session
        latest_ex_id = next(iter(per_ex_sets))
        from app.services.overload import SetSuggestion

        rec = recommend([per_ex_sets[latest_ex_id]])
        if rec:
            t = rec.target[0] if rec.target else SetSuggestion()
            load = t.weight if t.weight else (
                (t.bodyweight or 0) + (t.added_weight or 0)
            ) or None
            next_target = {
                "exercise_id": latest_ex_id,
                "exercise": ex_names[latest_ex_id],
                "action": rec.action,
                "headline": rec.headline,
                "weight": t.weight,
                "reps": t.reps,
                "added_weight": t.added_weight,
                "bodyweight": t.bodyweight,
            }

    # ---- recent PRs ----
    pr_rows = db.scalars(
        select(PersonalRecord)
        .where(PersonalRecord.user_id == user_id)
        .order_by(PersonalRecord.achieved_at.desc())
        .limit(5)
    ).all()
    recent_prs = []
    for pr in pr_rows:
        from app.models.exercise import Exercise

        ex = db.get(Exercise, pr.exercise_id)
        recent_prs.append(
            {
                "exercise": ex.name if ex else "?",
                "exercise_id": pr.exercise_id,
                "category": pr.category,
                "weight": pr.weight,
                "reps": pr.reps,
                "added_weight": pr.added_weight,
                "duration": pr.duration,
                "achieved_at": pr.achieved_at.isoformat() if pr.achieved_at else None,
            }
        )

    # ---- sessions this week (count only) ----
    week_start = date.fromordinal(today.toordinal() - today.weekday())
    week_dates = [
        d
        for d in streaks_service.completed_workout_dates(db, user_id)
        if week_start <= d <= today
    ]

    hour = __import__("datetime").datetime.now().hour
    if hour < 12:
        greeting = "GOOD MORNING"
    elif hour < 18:
        greeting = "GOOD AFTERNOON"
    else:
        greeting = "GOOD EVENING"

    return {
        "greeting": greeting,
        "date": today.isoformat(),
        "streak": streak,
        "todays_workout": todays,
        "mission": mission,
        "missions": [
            {
                "code": m.code,
                "description": m.description,
                "progress": m.progress,
                "target": m.target,
                "completed": m.completed,
            }
            for m in missions
        ],
        "next_target": next_target,
        "recent_prs": recent_prs,
        "weekly_sessions": len(week_dates),
        "recommendations": smart_recommendations(db, user_id, today),
    }
