"""Workout template service (spec §12, §13): routines CRUD with drag & drop
reordering and the "repeat last workout" snapshot."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.exercise import Exercise
from app.models.workout import (
    TemplateExercise,
    WorkoutExercise,
    WorkoutSession,
    WorkoutTemplate,
)

from app.services.errors import NotFoundError


def list_templates(db: Session, user_id: int) -> list[dict]:
    rows = db.scalars(
        select(WorkoutTemplate)
        .where(WorkoutTemplate.user_id == user_id)
        .order_by(WorkoutTemplate.name)
    ).all()
    return [_serialize(db, t) for t in rows]


def get_template(db: Session, user_id: int, template_id: int) -> dict:
    t = db.get(WorkoutTemplate, template_id)
    if t is None or t.user_id != user_id:
        raise NotFoundError("Template not found.")
    return _serialize(db, t)


def _serialize(db: Session, t: WorkoutTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "exercises": [
            {
                "id": te.id,
                "exercise_id": te.exercise_id,
                "name": db.get(Exercise, te.exercise_id).name,
                "position": te.position,
                "sets": te.sets,
                "rep_range_min": te.rep_range_min,
                "rep_range_max": te.rep_range_max,
                "rest_seconds": te.rest_seconds,
                "notes": te.notes,
            }
            for te in sorted(t.exercises, key=lambda e: e.position)
        ],
    }


def create_template(db: Session, user_id: int, payload: dict) -> dict:
    t = WorkoutTemplate(
        user_id=user_id, name=payload["name"], description=payload.get("description")
    )
    db.add(t)
    db.flush()
    for i, ex in enumerate(payload.get("exercises", [])):
        db.add(
            TemplateExercise(
                template_id=t.id,
                exercise_id=ex["exercise_id"],
                position=i,
                sets=ex.get("sets", 3),
                rep_range_min=ex.get("rep_range_min"),
                rep_range_max=ex.get("rep_range_max"),
                rest_seconds=ex.get("rest_seconds"),
                notes=ex.get("notes"),
            )
        )
    db.flush()
    return get_template(db, user_id, t.id)


def update_template(db: Session, user_id: int, template_id: int, payload: dict) -> dict:
    t = db.get(WorkoutTemplate, template_id)
    if t is None or t.user_id != user_id:
        raise NotFoundError("Template not found.")
    if "name" in payload:
        t.name = payload["name"]
    if "description" in payload:
        t.description = payload["description"]

    if "exercises" in payload:
        # full replace of exercise rows (positions included) — simple & safe
        for te in list(t.exercises):
            db.delete(te)
        db.flush()
        for i, ex in enumerate(payload["exercises"]):
            db.add(
                TemplateExercise(
                    template_id=t.id,
                    exercise_id=ex["exercise_id"],
                    position=i,
                    sets=ex.get("sets", 3),
                    rep_range_min=ex.get("rep_range_min"),
                    rep_range_max=ex.get("rep_range_max"),
                    rest_seconds=ex.get("rest_seconds"),
                    notes=ex.get("notes"),
                )
            )
    db.flush()
    return get_template(db, user_id, t.id)


def reorder_template_exercise(
    db: Session, user_id: int, template_id: int, item_id: int, new_position: int
) -> dict:
    """Drag & drop: move one exercise to a new position (0-indexed)."""
    t = db.get(WorkoutTemplate, template_id)
    if t is None or t.user_id != user_id:
        raise NotFoundError("Template not found.")
    items = sorted(t.exercises, key=lambda e: e.position)
    item = next((e for e in items if e.id == item_id), None)
    if item is None:
        raise NotFoundError("Exercise not in template.")
    items = [e for e in items if e.id != item_id]
    new_position = max(0, min(new_position, len(items)))
    items.insert(new_position, item)
    for i, e in enumerate(items):
        e.position = i
    db.flush()
    return get_template(db, user_id, template_id)


def delete_template(db: Session, user_id: int, template_id: int) -> None:
    t = db.get(WorkoutTemplate, template_id)
    if t is None or t.user_id != user_id:
        raise NotFoundError("Template not found.")
    db.delete(t)
    db.flush()


def previous_session_for_template(db: Session, user_id: int, template_id: int) -> dict | None:
    """The most recent completed session that used this template — the
    prefill reference for 'Start Previous Workout' (spec §13)."""
    sess = db.scalars(
        select(WorkoutSession)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.template_id == template_id,
            WorkoutSession.status == "completed",
        )
        .order_by(WorkoutSession.started_at.desc())
        .limit(1)
    ).first()
    if sess is None:
        # fall back to most recent session with the same name
        t = db.get(WorkoutTemplate, template_id)
        if t is None:
            return None
        sess = db.scalars(
            select(WorkoutSession)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.name == t.name,
                WorkoutSession.status == "completed",
            )
            .order_by(WorkoutSession.started_at.desc())
            .limit(1)
        ).first()
    if sess is None:
        return None

    return {
        "session_id": sess.id,
        "date": (sess.completed_at or sess.started_at).date().isoformat(),
        "name": sess.name,
        "exercises": [
            {
                "exercise_id": we.exercise_id,
                "name": we.exercise.name,
                "sets": [
                    {
                        "weight": s.weight,
                        "per_dumbbell": s.per_dumbbell,
                        "reps": s.reps,
                        "duration": s.duration,
                        "bodyweight": s.bodyweight,
                        "added_weight": s.added_weight,
                    }
                    for s in sorted(we.sets, key=lambda x: x.set_number)
                ],
            }
            for we in sorted(sess.exercises, key=lambda x: x.position)
        ],
    }
