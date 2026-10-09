"""Exercise library service: catalog + custom exercises, per-exercise history,
detail data (PRs, graphs, recommendation, notes)."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import ExerciseNote
from app.models.exercise import Exercise
from app.models.user import PersonalRecord
from app.models.workout import (
    WorkoutExercise,
    WorkoutSession,
    WorkoutSet,
)

from app.services.errors import NotFoundError
from app.services.metrics import effective_load, estimated_1rm, set_volume
from app.services.overload import recommend


def list_exercises(
    db: Session,
    user_id: int,
    *,
    group: str | None = None,
    q: str | None = None,
    exercise_type: str | None = None,
) -> list[dict]:
    stmt = select(Exercise).where(
        Exercise.owner_user_id.is_(None) | (Exercise.owner_user_id == user_id)
    )
    rows = db.scalars(stmt).all()
    out = []
    for ex in rows:
        primary = next((m for m in ex.muscles if m.is_primary), None)
        group_name = primary.muscle_group.name if primary else None
        out.append(
            {
                "id": ex.id,
                "name": ex.name,
                "exercise_type": ex.exercise_type,
                "resistance": ex.resistance,
                "dumbbell_pair": ex.dumbbell_pair,
                "primary_muscle": group_name,
                "is_custom": ex.owner_user_id is not None,
                "equipment_id": ex.equipment_id,
            }
        )
    if group:
        out = [e for e in out if (e["primary_muscle"] or "").lower() == group.lower()]
    if exercise_type:
        out = [e for e in out if e["exercise_type"] == exercise_type]
    if q:
        ql = q.lower()
        out = [e for e in out if ql in e["name"].lower()]
    return sorted(out, key=lambda e: e["name"])


def create_custom_exercise(db: Session, user_id: int, payload: dict) -> dict:
    ex = Exercise(
        name=payload["name"],
        owner_user_id=user_id,
        exercise_type=payload.get("exercise_type", "free_weight"),
        resistance=payload.get("resistance", "external"),
        dumbbell_pair=bool(payload.get("dumbbell_pair", False)),
        form_description=payload.get("form_description"),
        technique_tips=payload.get("technique_tips"),
    )
    db.add(ex)
    db.flush()
    primary_id = payload.get("primary_muscle_id")
    if primary_id:
        from app.models.association import ExerciseMuscle

        db.add(ExerciseMuscle(exercise_id=ex.id, muscle_group_id=primary_id, is_primary=True))
    db.flush()
    return {"id": ex.id, "name": ex.name}


def get_history(
    db: Session,
    user_id: int,
    exercise_id: int,
    *,
    range_key: str = "all",
) -> dict | None:
    """Per-exercise history page data (spec §6): bests, totals, sessions."""
    ex = db.get(Exercise, exercise_id)
    if ex is None:
        raise NotFoundError("Exercise not found.")

    rows = (
        db.execute(
            select(WorkoutSet, WorkoutSession)
            .join(WorkoutExercise, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .join(WorkoutSession, WorkoutExercise.session_id == WorkoutSession.id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutExercise.exercise_id == exercise_id,
                WorkoutSession.status == "completed",
            )
            .order_by(WorkoutSession.started_at.desc(), WorkoutSet.set_number)
        )
        .all()
    )

    from app.services.analytics import period_start

    start = period_start(range_key)
    filtered = [
        (s, sess) for s, sess in rows
        if start is None or (sess.completed_at or sess.started_at).date() >= start
    ]

    best_weight: float | None = None
    best_reps: tuple[int, float | None] | None = None  # (reps, weight)
    best_1rm: float | None = None
    best_volume_set: float | None = None
    best_duration: float | None = None
    best_volume_session: float | None = None
    session_dates: set[int] = set()
    total_sets = 0
    total_volume = 0.0

    sessions_out: dict[int, dict] = {}
    for s, sess in filtered:
        session_dates.add(sess.id)
        total_sets += 1
        load = effective_load(s)
        vol = set_volume(s)
        total_volume += vol
        best_volume_session = None  # computed below per-session

        if s.exercise_kind == "duration":
            if s.duration and (best_duration is None or s.duration > best_duration):
                best_duration = s.duration
        elif load is not None and s.reps is not None:
            if best_weight is None or load > best_weight:
                best_weight = load
            if best_reps is None or s.reps > best_reps[0]:
                best_reps = (s.reps, load)
            e = estimated_1rm(load, s.reps)
            if e and (best_1rm is None or e > best_1rm):
                best_1rm = e
            if best_volume_set is None or vol > best_volume_set:
                best_volume_set = vol

        entry = sessions_out.setdefault(
            sess.id,
            {"date": (sess.completed_at or sess.started_at).date().isoformat(), "sets": []},
        )
        entry["sets"].append(
            {
                "weight": s.weight,
                "per_dumbbell": s.per_dumbbell,
                "reps": s.reps,
                "duration": s.duration,
                "bodyweight": s.bodyweight,
                "added_weight": s.added_weight,
                "effective_load": load,
                "volume": round(vol, 1),
            }
        )

    # per-session volume
    per_session_vol: dict[int, float] = {}
    for s, sess in filtered:
        per_session_vol[sess.id] = per_session_vol.get(sess.id, 0.0) + set_volume(s)
    if per_session_vol:
        best_volume_session = max(per_session_vol.values())

    # chronological series for graphs
    series_by_date: dict[str, dict] = {}
    for s, sess in rows:
        if start is not None and (sess.completed_at or sess.started_at).date() < start:
            continue
        d = (sess.completed_at or sess.started_at).date().isoformat()
        entry = series_by_date.setdefault(
            d, {"date": d, "top_weight": 0.0, "top_reps": 0, "volume": 0.0, "sets": 0, "e1rm": 0.0}
        )
        load = effective_load(s)
        vol = set_volume(s)
        entry["volume"] += vol
        entry["sets"] += 1
        if load is not None:
            entry["top_weight"] = max(entry["top_weight"], load)
            e = estimated_1rm(load, s.reps) if s.reps else None
            if e:
                entry["e1rm"] = max(entry["e1rm"], e)
        if s.reps:
            entry["top_reps"] = max(entry["top_reps"], s.reps)

    series = [
        {
            "date": d["date"],
            "top_weight": round(d["top_weight"], 2) or None,
            "top_reps": d["top_reps"] or None,
            "volume": round(d["volume"], 1),
            "sets": d["sets"],
            "estimated_1rm": round(d["e1rm"], 1) or None,
        }
        for d in sorted(series_by_date.values(), key=lambda x: x["date"])
    ]

    # recommendation from chronological history
    chrono: dict[int, list[WorkoutSet]] = {}
    chrono_order: list[int] = []
    for s, sess in rows:
        if s.exercise_kind == "duration" and not s.reps:
            pass
        if sess.id not in chrono:
            chrono[sess.id] = []
            chrono_order.append(sess.id)
        chrono[sess.id].append(s)
    rec = recommend([chrono[sid] for sid in chrono_order]) if chrono_order else None

    from dataclasses import asdict

    prs = db.scalars(
        select(PersonalRecord).where(
            PersonalRecord.user_id == user_id,
            PersonalRecord.exercise_id == exercise_id,
        )
    ).all()

    return {
        "exercise": {
            "id": ex.id,
            "name": ex.name,
            "exercise_type": ex.exercise_type,
            "resistance": ex.resistance,
            "dumbbell_pair": ex.dumbbell_pair,
            "form_description": ex.form_description,
            "technique_tips": ex.technique_tips,
            "primary_muscle": (
                next((m.muscle_group.name for m in ex.muscles if m.is_primary), None)
            ),
            "secondary_muscles": [
                m.muscle_group.name for m in ex.muscles if not m.is_primary
            ],
        },
        "bests": {
            "heaviest_weight": best_weight,
            "most_reps": best_reps[0] if best_reps else None,
            "most_reps_weight": best_reps[1] if best_reps else None,
            "best_estimated_1rm": best_1rm,
            "best_volume_set": round(best_volume_set, 1) if best_volume_set else None,
            "best_volume_session": round(best_volume_session, 1) if best_volume_session else None,
            "longest_duration": best_duration,
        },
        "totals": {
            "sessions": len(session_dates),
            "sets": total_sets,
            "total_volume": round(total_volume, 1),
        },
        "sessions": list(sessions_out.values()),
        "series": series,
        "recommendation": asdict(rec) if rec else None,
        "prs": [
            {
                "category": pr.category,
                "value": pr.value,
                "weight": pr.weight,
                "reps": pr.reps,
                "added_weight": pr.added_weight,
                "duration": pr.duration,
                "achieved_at": pr.achieved_at.isoformat() if pr.achieved_at else None,
            }
            for pr in prs
        ],
    }


def get_note(db: Session, user_id: int, exercise_id: int) -> str | None:
    row = db.scalar(
        select(ExerciseNote).where(
            ExerciseNote.user_id == user_id,
            ExerciseNote.exercise_id == exercise_id,
        )
    )
    return row.note if row else None


def set_note(db: Session, user_id: int, exercise_id: int, note: str) -> None:
    row = db.scalar(
        select(ExerciseNote).where(
            ExerciseNote.user_id == user_id,
            ExerciseNote.exercise_id == exercise_id,
        )
    )
    if row is None:
        row = ExerciseNote(user_id=user_id, exercise_id=exercise_id, note=note)
        db.add(row)
    else:
        row.note = note
    db.flush()
