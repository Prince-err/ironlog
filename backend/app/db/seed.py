"""Development seed data (idempotent).

Seeds muscle groups, equipment, the exercise catalog, a demo user and the
starter Push/Pull/Legs templates. No workout history is created — the app
starts with a clean log so real training data can be logged from day one.

(Test suites build their own fictional history via `tests/demo_history.py`.)
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.exercise_data import (
    EQUIPMENT,
    EXERCISES,
    MUSCLE_GROUPS,
    MUSCLES,
    ExerciseDef,
)
from app.models import (
    Equipment,
    Exercise,
    ExerciseMuscle,
    MuscleGroup,
    User,
    UserSettings,
    WorkoutTemplate,
    TemplateExercise,
)

DEMO_USER_EMAIL = "demo@ironlog.app"


def _ensure_muscles_and_equipment(db: Session) -> dict[str, int]:
    muscle_ids: dict[str, int] = {}
    for s, name in MUSCLES:
        row = db.scalar(select(MuscleGroup).where(MuscleGroup.slug == s))
        if row is None:
            row = MuscleGroup(slug=s, name=name)
            db.add(row)
            db.flush()
        muscle_ids[s] = row.id
    for s, name in MUSCLE_GROUPS:
        if db.scalar(select(MuscleGroup).where(MuscleGroup.slug == s)) is None:
            db.add(MuscleGroup(slug=s, name=name))
    equipment_ids: dict[str, int] = {}
    for s, name in EQUIPMENT:
        row = db.scalar(select(Equipment).where(Equipment.slug == s))
        if row is None:
            row = Equipment(slug=s, name=name)
            db.add(row)
            db.flush()
        equipment_ids[s] = row.id
    db.flush()
    return {"muscles": muscle_ids, "equipment": equipment_ids}


def _exercise_from_def(d: ExerciseDef, ids) -> Exercise:
    ex = Exercise(
        name=d.name,
        exercise_type=d.etype,
        resistance=d.resistance,
        equipment_id=ids["equipment"].get(d.equipment),
        primary_muscle_id=ids["muscles"].get(d.primary),
        dumbbell_pair=d.dumbbell_pair,
        form_description=d.form or None,
        technique_tips=d.tips or None,
    )
    ex.muscles = [
        ExerciseMuscle(muscle_group_id=ids["muscles"][d.primary], is_primary=True)
    ]
    for m in d.secondary:
        ex.muscles.append(
            ExerciseMuscle(muscle_group_id=ids["muscles"][m], is_primary=False)
        )
    return ex


def ensure_exercise_catalog(db: Session) -> dict[str, Exercise]:
    """Seed all catalog exercises; return name -> Exercise map."""
    ids = _ensure_muscles_and_equipment(db)
    by_name: dict[str, Exercise] = {}
    existing = db.scalars(select(Exercise).where(Exercise.owner_user_id.is_(None))).all()
    for ex in existing:
        by_name[ex.name] = ex
    for d in EXERCISES:
        if d.name in by_name:
            continue
        ex = _exercise_from_def(d, ids)
        db.add(ex)
        db.flush()
        by_name[d.name] = ex
    db.flush()
    return by_name


def ensure_demo_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == DEMO_USER_EMAIL))
    if user is None:
        user = User(
            email=DEMO_USER_EMAIL,
            name="Demo Lifter",
            bodyweight_kg=78.0,
            unit="kg",
        )
        db.add(user)
        db.flush()
    settings = db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
    if settings is None:
        db.add(UserSettings(user_id=user.id, unit="kg", default_rest_seconds=90))
    db.flush()
    return user


def _seed_templates(db: Session, user: User, catalog: dict[str, Exercise]) -> None:
    for name, rows in {
        "Push": [
            ("Bench Press", 3, 8, 12, 150),
            ("Incline Dumbbell Press", 3, 8, 12, 120),
            ("Overhead Press", 3, 6, 8, 150),
            ("Lateral Raise", 4, 12, 15, 60),
            ("Triceps Pushdown", 3, 12, 15, 60),
        ],
        "Pull": [
            ("Pull-Ups", 3, 6, 10, 120),
            ("Lat Pulldown", 3, 8, 12, 120),
            ("Seated Cable Row", 3, 8, 12, 90),
            ("Face Pull", 3, 15, 20, 60),
            ("Barbell Curl", 3, 8, 12, 60),
        ],
        "Legs": [
            ("Barbell Squat", 3, 5, 8, 180),
            ("Romanian Deadlift", 3, 8, 10, 150),
            ("Leg Press", 3, 10, 12, 120),
            ("Leg Curl", 3, 10, 15, 90),
            ("Standing Calf Raise", 4, 12, 20, 60),
        ],
    }.items():
        existing = db.scalar(
            select(WorkoutTemplate.id).where(
                WorkoutTemplate.user_id == user.id, WorkoutTemplate.name == name
            )
        )
        if existing is not None:
            continue
        t = WorkoutTemplate(user_id=user.id, name=name)
        db.add(t)
        db.flush()
        for i, (ex_name, sets, rmin, rmax, rest) in enumerate(rows):
            db.add(
                TemplateExercise(
                    template_id=t.id,
                    exercise_id=catalog[ex_name].id,
                    position=i,
                    sets=sets,
                    rep_range_min=rmin,
                    rep_range_max=rmax,
                    rest_seconds=rest,
                )
            )


def seed(db: Session) -> None:
    """Seed catalog, demo user and starter templates (no workout history)."""
    catalog = ensure_exercise_catalog(db)
    user = ensure_demo_user(db)
    _seed_templates(db, user, catalog)


if __name__ == "__main__":
    from app.db.base import Base
    from app.db.session import get_session_factory

    # Import models so create_all sees the full metadata, then create tables.
    import app.models  # noqa: F401

    engine = get_session_factory().kw["bind"]
    Base.metadata.create_all(engine)

    factory = get_session_factory()
    s = factory()
    try:
        seed(s)
        s.commit()
        print("Seed complete (demo user: demo@ironlog.app)")
    finally:
        s.close()
