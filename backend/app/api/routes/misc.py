"""Dashboard, history, PRs, missions, templates, analytics, profile routes."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import (
    BodyweightLog,
    MissionCompletion,
    PersonalRecord,
    User,
    UserSettings,
)
from app.models.workout import WorkoutSession
from app.schemas.common import (
    BodyweightIn,
    SettingsIn,
    TemplateIn,
    TemplateReorderIn,
)
from app.services import (
    analytics as analytics_service,
    dashboard as dashboard_service,
    missions as missions_service,
    sessions as sessions_service,
    templates as templates_service,
)

router = APIRouter(tags=["app"])


# ---------------------------------------------------------------- dashboard


@router.get("/dashboard", summary="Home screen data")
def dashboard(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return dashboard_service.dashboard(db, user.id)


@router.get("/heatmap", summary="Training heatmap data")
def heatmap(
    days: int = Query(default=182, le=365),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return analytics_service.heatmap(db, user.id, days)


# ----------------------------------------------------------------- history


@router.get("/history", summary="Workout history list")
def history(
    limit: int = Query(default=30, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(WorkoutSession)
        .where(WorkoutSession.user_id == user.id, WorkoutSession.status == "completed")
        .order_by(WorkoutSession.started_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "date": (s.completed_at or s.started_at).date().isoformat(),
            "exercises": len(s.exercises),
            "sets": sum(len(we.sets) for we in s.exercises),
            "volume": round(
                sum(
                    x.weight * x.reps
                    for we in s.exercises
                    for x in we.sets
                    if x.weight and x.reps
                ),
                1,
            ),
        }
        for s in rows
    ]


@router.get("/sessions/{session_id}/summary", summary="Post-workout summary")
def session_summary_route(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return sessions_service.session_summary(db, user.id, session_id)


# -------------------------------------------------------------------- PRs


@router.get("/prs", summary="All personal records grouped by exercise")
def all_prs(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    rows = db.scalars(
        select(PersonalRecord)
        .where(PersonalRecord.user_id == user.id)
        .order_by(PersonalRecord.achieved_at.desc())
    ).all()
    from app.models.exercise import Exercise

    out: dict[int, dict] = {}
    for pr in rows:
        ex = db.get(Exercise, pr.exercise_id)
        entry = out.setdefault(
            pr.exercise_id,
            {"exercise_id": pr.exercise_id, "exercise": ex.name if ex else "?", "records": []},
        )
        entry["records"].append(
            {
                "category": pr.category,
                "value": pr.value,
                "weight": pr.weight,
                "reps": pr.reps,
                "added_weight": pr.added_weight,
                "bodyweight": pr.bodyweight,
                "duration": pr.duration,
                "achieved_at": pr.achieved_at.isoformat() if pr.achieved_at else None,
            }
        )
    return list(out.values())


# ---------------------------------------------------------------- missions


@router.get("/missions/today", summary="Today's missions")
def missions_today(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    rows = missions_service.generate_daily_missions(db, user.id, date.today())
    return [
        {
            "code": m.code,
            "description": m.description,
            "progress": m.progress,
            "target": m.target,
            "completed": m.completed,
        }
        for m in rows
    ]


# --------------------------------------------------------------- templates


@router.get("/templates", summary="List workout templates")
def list_templates(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return templates_service.list_templates(db, user.id)


@router.post("/templates", status_code=201, summary="Create a template")
def create_template(
    payload: TemplateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return templates_service.create_template(db, user.id, payload.model_dump())


@router.get("/templates/{template_id}", summary="Template detail")
def get_template(
    template_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return templates_service.get_template(db, user.id, template_id)


@router.put("/templates/{template_id}", summary="Update a template")
def update_template(
    template_id: int,
    payload: TemplateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return templates_service.update_template(db, user.id, template_id, payload.model_dump())


@router.put("/templates/{template_id}/reorder", summary="Drag & drop reorder")
def reorder_template(
    template_id: int,
    payload: TemplateReorderIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return templates_service.reorder_template_exercise(
        db, user.id, template_id, payload.item_id, payload.new_position
    )


@router.delete("/templates/{template_id}", summary="Delete a template")
def delete_template(
    template_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    templates_service.delete_template(db, user.id, template_id)
    return {"ok": True}


@router.get("/templates/{template_id}/previous", summary="Repeat-last snapshot")
def template_previous(
    template_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return templates_service.previous_session_for_template(db, user.id, template_id)


# --------------------------------------------------------------- analytics


@router.get("/analytics/summary", summary="Volume/frequency summary")
def analytics_summary(
    range: str = Query(default="30d"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return analytics_service.volume_summary(db, user.id, range)


@router.get("/analytics/muscle-groups", summary="Volume by muscle group")
def analytics_muscles(
    range: str = Query(default="30d"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return analytics_service.muscle_group_volume(db, user.id, range)


@router.get("/analytics/strength", summary="Strength progression per exercise")
def analytics_strength(
    weeks: int = Query(default=6, le=52),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return analytics_service.strength_progression(db, user.id, weeks)


@router.get("/analytics/recommendations", summary="Smart insights")
def analytics_recommendations(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return {"recommendations": analytics_service.smart_recommendations(db, user.id)}


# ----------------------------------------------------------------- profile


@router.get("/me", summary="Profile + settings")
def get_me(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    settings = db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "bodyweight_kg": user.bodyweight_kg,
        "unit": settings.unit if settings else user.unit,
        "default_rest_seconds": settings.default_rest_seconds if settings else 90,
    }


@router.put("/me", summary="Update profile/settings")
def update_me(
    payload: SettingsIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.unit:
        user.unit = payload.unit
    if payload.name:
        user.name = payload.name
    if payload.bodyweight_kg:
        user.bodyweight_kg = payload.bodyweight_kg
    settings = db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
    if settings is None:
        settings = UserSettings(user_id=user.id)
        db.add(settings)
    if payload.unit:
        settings.unit = payload.unit
    if payload.default_rest_seconds:
        settings.default_rest_seconds = payload.default_rest_seconds
    db.flush()
    return get_me(user=user, db=db)


@router.get("/me/bodyweight", summary="Bodyweight log")
def get_bodyweight(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    rows = db.scalars(
        select(BodyweightLog)
        .where(BodyweightLog.user_id == user.id)
        .order_by(BodyweightLog.log_date.desc())
        .limit(90)
    ).all()
    return [
        {"date": r.log_date.isoformat(), "weight_kg": r.weight_kg} for r in rows
    ]


@router.post("/me/bodyweight", status_code=201, summary="Log bodyweight")
def post_bodyweight(
    payload: BodyweightIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log_date = date.fromisoformat(payload.log_date) if payload.log_date else date.today()
    row = db.scalar(
        select(BodyweightLog).where(
            BodyweightLog.user_id == user.id, BodyweightLog.log_date == log_date
        )
    )
    if row is None:
        row = BodyweightLog(user_id=user.id, log_date=log_date, weight_kg=payload.weight_kg)
        db.add(row)
    else:
        row.weight_kg = payload.weight_kg
    user.bodyweight_kg = payload.weight_kg
    db.flush()
    return {"date": row.log_date.isoformat(), "weight_kg": row.weight_kg}
