"""Exercise routes: library browsing, custom exercises, per-exercise history."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import CustomExerciseIn, NoteIn
from app.services import exercises as exercises_service

router = APIRouter(tags=["exercises"])


@router.get("/exercises", summary="Browse the exercise library")
def list_exercises(
    group: str | None = Query(default=None, description="Filter by muscle group name"),
    type: str | None = Query(default=None, description="bodyweight|free_weight|machine|cable|duration"),
    q: str | None = Query(default=None, description="Name search"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return exercises_service.list_exercises(
        db, user.id, group=group, q=q, exercise_type=type
    )


@router.get("/muscle-groups", summary="All muscle groups (for pickers/forms)")
def muscle_groups(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.reference import MuscleGroup

    rows = db.scalars(select(MuscleGroup).order_by(MuscleGroup.name)).all()
    return [{"id": m.id, "slug": m.slug, "name": m.name} for m in rows]


@router.post("/exercises", status_code=201, summary="Create a custom exercise")
def create_exercise(
    payload: CustomExerciseIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return exercises_service.create_custom_exercise(db, user.id, payload.model_dump())


@router.get("/exercises/{exercise_id}/history", summary="Full history for one exercise")
def exercise_history(
    exercise_id: int,
    range: str = Query(default="all", description="7d|30d|3m|6m|1y|all"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return exercises_service.get_history(db, user.id, exercise_id, range_key=range)


@router.get("/exercises/{exercise_id}/note", summary="Get personal note")
def get_note(
    exercise_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"note": exercises_service.get_note(db, user.id, exercise_id)}


@router.put("/exercises/{exercise_id}/note", summary="Save personal note")
def put_note(
    exercise_id: int,
    payload: NoteIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exercises_service.set_note(db, user.id, exercise_id, payload.note)
    return {"ok": True}
