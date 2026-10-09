"""Workout session routes: the core logging loop."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import (
    AddExerciseIn,
    ReorderIn,
    SetIn,
    SetUpdateIn,
    StartSessionIn,
)
from app.services import sessions as sessions_service

router = APIRouter(tags=["workouts"])


@router.get("/sessions/active", summary="Current in-progress session")
def active_session(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    s = sessions_service.get_active_session(db, user.id)
    if s is None:
        return None
    return sessions_service.session_summary(db, user.id, s.id)


@router.post("/sessions/start", status_code=201, summary="Start a workout")
def start_session(
    payload: StartSessionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = sessions_service.start_session(
        db,
        user.id,
        template_id=payload.template_id,
        name=payload.name,
        exercise_ids=payload.exercise_ids,
    )
    return sessions_service.session_summary(db, user.id, session.id)


@router.get("/sessions/{session_id}", summary="Session detail")
def get_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return sessions_service.session_summary(db, user.id, session_id)


@router.post("/sessions/{session_id}/exercises", status_code=201,
             summary="Add an exercise to the session")
def add_exercise(
    session_id: int,
    payload: AddExerciseIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    we = sessions_service.add_exercise_to_session(
        db, user.id, session_id, payload.exercise_id
    )
    return {"workout_exercise_id": we.id}


@router.delete("/sessions/{session_id}/exercises/{workout_exercise_id}",
               summary="Remove an exercise from the session")
def remove_exercise(
    session_id: int,
    workout_exercise_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions_service.remove_exercise(db, user.id, workout_exercise_id)
    return {"ok": True}


@router.put("/sessions/{session_id}/exercises/{workout_exercise_id}/position",
            summary="Reorder an exercise (drag & drop)")
def reorder_exercise(
    session_id: int,
    workout_exercise_id: int,
    payload: ReorderIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions_service.reorder_exercise(
        db, user.id, workout_exercise_id, payload.new_position
    )
    return {"ok": True}


@router.post("/workout-exercises/{workout_exercise_id}/sets", status_code=201,
             summary="Log a set")
def log_set(
    workout_exercise_id: int,
    payload: SetIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = sessions_service.log_set(db, user.id, workout_exercise_id, payload.model_dump())
    return {
        "id": s.id,
        "set_number": s.set_number,
        "weight": s.weight,
        "per_dumbbell": s.per_dumbbell,
        "reps": s.reps,
        "duration": s.duration,
        "bodyweight": s.bodyweight,
        "added_weight": s.added_weight,
        "exercise_kind": s.exercise_kind,
    }


@router.patch("/sets/{set_id}", summary="Edit a logged set")
def update_set(
    set_id: int,
    payload: SetUpdateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = sessions_service.update_set(db, user.id, set_id, payload.model_dump(exclude_none=True))
    return {"id": s.id, "weight": s.weight, "reps": s.reps, "duration": s.duration}


@router.delete("/sets/{set_id}", summary="Delete a logged set")
def delete_set(
    set_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions_service.delete_set(db, user.id, set_id)
    return {"ok": True}


@router.get("/exercises/{exercise_id}/previous", summary="Previous performance + recommendation")
def previous_performance(
    exercise_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return sessions_service.previous_performance(db, user.id, exercise_id)


@router.post("/sessions/{session_id}/complete", summary="Complete the workout")
def complete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return sessions_service.complete_session(db, user.id, session_id)
