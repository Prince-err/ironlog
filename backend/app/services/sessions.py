"""Workout session service — the core workout engine.

Handles: starting sessions (blank, from template, or repeat-last), logging
sets with per-type validation, computing previous performance for the
"beat this" reference, and completing sessions (PRs, streak, missions,
summary).
"""

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.exercise import Exercise
from app.models.user import User
from app.models.workout import (
    TemplateExercise,
    WorkoutExercise,
    WorkoutSession,
    WorkoutSet,
    WorkoutTemplate,
)

from app.services import missions as missions_service
from app.services import prs as prs_service
from app.services import streaks as streaks_service
from app.services.errors import ConflictError, NotFoundError, ValidationError
from app.services.metrics import effective_load, set_volume


def _kind_for(exercise: Exercise) -> str:
    return {
        "bodyweight": "bodyweight",
        "bodyweight_weighted": "bodyweight_weighted",
        "external": "weight",
        "duration": "duration",
    }[exercise.resistance]


# ------------------------------------------------------------- start session


def start_session(
    db: Session,
    user_id: int,
    *,
    template_id: int | None = None,
    repeat_last_template_id: int | None = None,
    name: str | None = None,
    exercise_ids: list[int] | None = None,
) -> WorkoutSession:
    """Start a new in-progress session.

    - template_id: copy the template's exercise order/prescription.
    - repeat_last_template_id: prefill from the most recent completed session
      that used this template (reference values only — nothing auto-submitted).
    - exercise_ids: blank session with a chosen list of exercises.
    """
    active = get_active_session(db, user_id)
    if active is not None:
        raise ConflictError("You already have a workout in progress.")

    session = WorkoutSession(user_id=user_id, name=name, status="in_progress")
    db.add(session)
    db.flush()

    if template_id is not None:
        tpl = db.get(WorkoutTemplate, template_id)
        if tpl is None or tpl.user_id != user_id:
            raise NotFoundError("Template not found.")
        session.name = session.name or tpl.name
        for te in tpl.exercises:
            we = WorkoutExercise(
                session_id=session.id,
                exercise_id=te.exercise_id,
                position=te.position,
                notes=te.notes,
            )
            db.add(we)
    elif exercise_ids:
        for pos, eid in enumerate(exercise_ids):
            db.add(
                WorkoutExercise(session_id=session.id, exercise_id=eid, position=pos)
            )

    db.flush()
    return session


def get_active_session(db: Session, user_id: int) -> WorkoutSession | None:
    return db.scalars(
        select(WorkoutSession)
        .where(WorkoutSession.user_id == user_id, WorkoutSession.status == "in_progress")
        .order_by(WorkoutSession.started_at.desc())
        .limit(1)
    ).first()


def add_exercise_to_session(
    db: Session, user_id: int, session_id: int, exercise_id: int
) -> WorkoutExercise:
    session = _owned_session(db, user_id, session_id)
    if db.get(Exercise, exercise_id) is None:
        raise NotFoundError("Exercise not found.")
    pos = len(session.exercises)
    we = WorkoutExercise(session_id=session.id, exercise_id=exercise_id, position=pos)
    db.add(we)
    db.flush()
    return we


def remove_exercise(db: Session, user_id: int, workout_exercise_id: int) -> None:
    we = db.get(WorkoutExercise, workout_exercise_id)
    if we is None:
        raise NotFoundError("Exercise not found in session.")
    session = _owned_session(db, user_id, we.session_id)
    session.exercises = [e for e in session.exercises if e.id != we.id]
    db.delete(we)
    db.flush()


def reorder_exercise(db: Session, user_id: int, workout_exercise_id: int, new_position: int) -> None:
    we = db.get(WorkoutExercise, workout_exercise_id)
    if we is None:
        raise NotFoundError("Exercise not found in session.")
    _owned_session(db, user_id, we.session_id)
    siblings = sorted(we.session.exercises, key=lambda e: e.position)
    siblings = [e for e in siblings if e.id != we.id]
    new_position = max(0, min(new_position, len(siblings)))
    siblings.insert(new_position, we)
    for i, e in enumerate(siblings):
        e.position = i
    db.flush()


def _owned_session(db: Session, user_id: int, session_id: int) -> WorkoutSession:
    s = db.get(WorkoutSession, session_id)
    if s is None:
        raise NotFoundError("Session not found.")
    if s.user_id != user_id:
        raise ConflictError("This session belongs to another user.")
    return s


# -------------------------------------------------------------- set logging


def log_set(
    db: Session,
    user_id: int,
    workout_exercise_id: int,
    payload: dict,
) -> WorkoutSet:
    """Log one set with per-type validation. Sparse by design:
    irrelevant fields stay NULL (spec §18, §25)."""
    we = db.get(WorkoutExercise, workout_exercise_id)
    if we is None:
        raise NotFoundError("Exercise not found in session.")
    session = _owned_session(db, user_id, we.session_id)
    if session.status != "in_progress":
        raise ConflictError("Workout already completed.")
    exercise = db.get(Exercise, we.exercise_id)
    if exercise is None:
        raise NotFoundError("Exercise not found.")

    kind = _kind_for(exercise)
    weight = payload.get("weight")
    reps = payload.get("reps")
    duration = payload.get("duration")
    added_weight = payload.get("added_weight")
    bodyweight = payload.get("bodyweight")
    per_dumbbell = payload.get("per_dumbbell")
    machine_type = payload.get("machine_type")
    machine_name = payload.get("machine_name")
    stack_value = payload.get("stack_value")
    rest_time = payload.get("rest_time")
    tempo = payload.get("tempo")
    notes = payload.get("notes")

    resistance_type = kind
    if kind == "weight":
        if weight is None or weight <= 0:
            raise ValidationError("Weight is required for load-based exercises.")
        if exercise.resistance == "external" and exercise.exercise_type == "free_weight":
            pass  # per_dumbbell allowed only for dumbbell exercises; harmless otherwise
        if machine_name and not machine_type:
            machine_type = "plate_loaded"
    elif kind == "bodyweight":
        if reps is None or reps < 0:
            raise ValidationError("Reps are required for bodyweight exercises.")
        if added_weight:
            kind = "bodyweight_weighted"
            resistance_type = "bodyweight_weighted"
            if bodyweight is None:
                bodyweight = user_bodyweight(db, user_id)
            if not added_weight or added_weight <= 0:
                raise ValidationError("Added weight must be positive.")
    elif kind == "bodyweight_weighted":
        if reps is None or reps < 0:
            raise ValidationError("Reps are required for bodyweight exercises.")
        if bodyweight is None:
            bodyweight = user_bodyweight(db, user_id)
        if not added_weight or added_weight <= 0:
            raise ValidationError(
                "Added weight is required for weighted bodyweight sets. "
                "Leave it empty to log bodyweight-only."
            )
    elif kind == "duration":
        if not duration or duration <= 0:
            raise ValidationError("Duration (seconds) is required for timed exercises.")
        reps = None  # timed holds don't take reps

    if kind in ("weight", "bodyweight_weighted") and (reps is None or reps < 0):
        raise ValidationError("Reps are required.")

    s = WorkoutSet(
        workout_exercise_id=we.id,
        exercise_kind=kind,
        set_number=len(we.sets) + 1,
        weight=float(weight) if weight is not None else None,
        per_dumbbell=bool(per_dumbbell) if per_dumbbell is not None else None,
        bodyweight=float(bodyweight) if bodyweight is not None else None,
        added_weight=float(added_weight) if added_weight is not None else None,
        duration=float(duration) if duration is not None else None,
        reps=reps,
        resistance_type=resistance_type,
        machine_type=machine_type,
        machine_name=machine_name,
        stack_value=float(stack_value) if stack_value is not None else None,
        rest_time=rest_time,
        tempo=tempo,
        notes=notes,
    )
    db.add(s)
    db.flush()
    missions_service.update_missions_after_set(db, user_id, len(session.exercises))
    return s


def delete_set(db: Session, user_id: int, set_id: int) -> None:
    s = db.get(WorkoutSet, set_id)
    if s is None:
        raise NotFoundError("Set not found.")
    we = db.get(WorkoutExercise, s.workout_exercise_id)
    session = _owned_session(db, user_id, we.session_id)
    if session.status != "in_progress":
        raise ConflictError("Workout already completed.")
    db.delete(s)
    db.flush()


def update_set(db: Session, user_id: int, set_id: int, payload: dict) -> WorkoutSet:
    s = db.get(WorkoutSet, set_id)
    if s is None:
        raise NotFoundError("Set not found.")
    we = db.get(WorkoutExercise, s.workout_exercise_id)
    session = _owned_session(db, user_id, we.session_id)
    if session.status != "in_progress":
        raise ConflictError("Workout already completed.")
    for field in ("weight", "reps", "duration", "notes", "rest_time"):
        if field in payload and payload[field] is not None:
            setattr(s, field, payload[field])
    db.flush()
    return s


# -------------------------------------------------------- previous session


def previous_performance(
    db: Session, user_id: int, exercise_id: int
) -> dict | None:
    """The most recent completed performance of this exercise (spec §4).

    Returns exercise fields + sets + the active overload recommendation so
    the UI can show "Last time: 80 × 8, 80 × 8, 75 × 10" right above input.
    """
    ex = db.get(Exercise, exercise_id)
    if ex is None:
        raise NotFoundError("Exercise not found.")

    rows = db.scalars(
        select(WorkoutSet)
        .join(WorkoutExercise, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
        .join(WorkoutSession, WorkoutExercise.session_id == WorkoutSession.id)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutExercise.exercise_id == exercise_id,
            WorkoutSession.status == "completed",
        )
        .order_by(WorkoutSession.started_at.desc(), WorkoutSet.set_number)
    ).all()

    if not rows:
        return None

    latest_session_id = rows[0].workout_exercise.session_id
    last_sets = [s for s in rows if s.workout_exercise.session_id == latest_session_id]
    last_sets.sort(key=lambda s: s.set_number)

    # chronological session history (oldest -> newest) for the engine
    by_session: dict[int, list[WorkoutSet]] = {}
    order: list[int] = []
    for s in reversed(rows):  # rows are newest-first
        sid = s.workout_exercise.session_id
        if sid not in by_session:
            by_session[sid] = []
            order.append(sid)
        by_session[sid].append(s)
    ordered_history = [by_session[sid] for sid in order]

    from app.services.overload import recommend

    rec = recommend(ordered_history)
    last_session = db.get(WorkoutSession, latest_session_id)

    return {
        "session_id": latest_session_id,
        "session_date": (
            last_session.completed_at or last_session.started_at
        ).date().isoformat(),
        "sets": [
            {
                "weight": s.weight,
                "per_dumbbell": s.per_dumbbell,
                "reps": s.reps,
                "duration": s.duration,
                "bodyweight": s.bodyweight,
                "added_weight": s.added_weight,
            }
            for s in last_sets
        ],
        "recommendation": _serialize_rec(rec),
    }


def _serialize_rec(rec) -> dict | None:
    if rec is None:
        return None
    from dataclasses import asdict

    d = asdict(rec)
    return d


# ----------------------------------------------------------------- complete


def complete_session(db: Session, user_id: int, session_id: int) -> dict:
    """Complete a session: recompute PRs, streak, missions; return summary."""
    session = _owned_session(db, user_id, session_id)
    if session.status != "in_progress":
        raise ConflictError("Workout already completed.")
    if not session.exercises:
        raise ValidationError("Add at least one exercise before completing.")

    exercise_count = len(session.exercises)
    set_count = 0
    volume = 0.0
    pr_count = 0
    new_prs: list[dict] = []

    # Mark the session completed FIRST so its sets are included in the
    # "completed sessions" scope that PR recomputation reads.
    now = datetime.now(timezone.utc)
    session.status = "completed"
    session.completed_at = now
    db.flush()

    for we in session.exercises:
        for s in we.sets:
            set_count += 1
            volume += set_volume(s)
        new = prs_service.recompute_user_prs(db, user_id, we.exercise_id)
        for pr in new:
            pr_count += 1
            new_prs.append(
                {
                    "exercise": we.exercise.name,
                    "category": pr.category,
                    "weight": pr.weight,
                    "reps": pr.reps,
                    "added_weight": pr.added_weight,
                    "duration": pr.duration,
                    "value": pr.value,
                }
            )

    db.flush()

    streaks_service.refresh_streak_state(db, user_id)
    missions_service.complete_missions_on_session_complete(
        db, user_id, exercise_count, pr_count, volume
    )

    # previous completed session volume for the delta (spec §15)
    prev = db.scalars(
        select(WorkoutSession)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.status == "completed",
            WorkoutSession.id != session.id,
        )
        .order_by(WorkoutSession.started_at.desc())
        .limit(1)
    ).first()
    prev_volume = 0.0
    if prev:
        for we in prev.exercises:
            for s in we.sets:
                prev_volume += set_volume(s)

    streak = streaks_service.compute_streak(db, user_id)
    duration_min = 0.0
    if session.started_at and session.completed_at:
        started = session.started_at
        ended = session.completed_at
        if started.tzinfo is None and ended.tzinfo is not None:
            started = started.replace(tzinfo=ended.tzinfo)
        elif ended.tzinfo is None and started.tzinfo is not None:
            ended = ended.replace(tzinfo=started.tzinfo)
        duration_min = (ended - started).total_seconds() / 60

    return {
        "session_id": session.id,
        "duration_minutes": round(duration_min),
        "exercises": exercise_count,
        "sets": set_count,
        "volume": round(volume, 1),
        "pr_count": pr_count,
        "new_prs": new_prs,
        "previous_volume": round(prev_volume, 1),
        "volume_delta": round(volume - prev_volume, 1),
        "streak": streak,
    }


def session_summary(db: Session, user_id: int, session_id: int) -> dict:
    """Full detail of a session (used for history + summary pages)."""
    s = _owned_session(db, user_id, session_id)
    return _serialize_session(db, s)


def _serialize_session(db: Session, s: WorkoutSession) -> dict:
    exercises = []
    volume = 0.0
    for we in s.exercises:
        ex = we.exercise
        sets = []
        for st in we.sets:
            v = set_volume(st)
            volume += v
            sets.append(
                {
                    "id": st.id,
                    "set_number": st.set_number,
                    "weight": st.weight,
                    "per_dumbbell": st.per_dumbbell,
                    "reps": st.reps,
                    "duration": st.duration,
                    "bodyweight": st.bodyweight,
                    "added_weight": st.added_weight,
                    "machine_type": st.machine_type,
                    "machine_name": st.machine_name,
                    "rest_time": st.rest_time,
                    "tempo": st.tempo,
                    "notes": st.notes,
                    "effective_load": effective_load(st),
                    "volume": round(v, 1),
                }
            )
        primary = next((m for m in ex.muscles if m.is_primary), None)
        exercises.append(
            {
                "workout_exercise_id": we.id,
                "exercise_id": ex.id,
                "name": ex.name,
                "exercise_type": ex.exercise_type,
                "resistance": ex.resistance,
                "primary_muscle": primary.muscle_group.name if primary else None,
                "notes": we.notes,
                "sets": sets,
            }
        )
    return {
        "id": s.id,
        "name": s.name,
        "status": s.status,
        "started_at": s.started_at.isoformat(),
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        "volume": round(volume, 1),
        "exercises": exercises,
    }


def user_bodyweight(db: Session, user_id: int) -> float | None:
    """Latest known bodyweight (log first, then profile value)."""
    from app.models.user import BodyweightLog

    row = db.scalars(
        select(BodyweightLog)
        .where(BodyweightLog.user_id == user_id)
        .order_by(BodyweightLog.log_date.desc())
        .limit(1)
    ).first()
    if row:
        return row.weight_kg
    u = db.get(User, user_id)
    return u.bodyweight_kg if u else None
