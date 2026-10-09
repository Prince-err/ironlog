"""Workout models: templates (routines) and live sessions.

WorkoutTemplate / TemplateExercise — reusable routines (Push/Pull/Legs ...)
with per-exercise sets, rep range, rest and notes, ordered for drag & drop.

WorkoutSession / WorkoutExercise / WorkoutSet — a logged training day.
Sets are intentionally sparse (spec §18/§25): a plank never stores a weight;
a lat pulldown never stores a duration. Columns are NULL when irrelevant and
validated by service logic instead of fake defaults.

For bodyweight+added-weight work (spec §19) three values are stored
separately: bodyweight, added_weight and computed total_resistance.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# ---------------------------------------------------------------- templates


class WorkoutTemplate(Base):
    __tablename__ = "workout_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    exercises: Mapped[list["TemplateExercise"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateExercise.position",
    )


class TemplateExercise(Base):
    __tablename__ = "template_exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("workout_templates.id", ondelete="CASCADE"), index=True
    )
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    position: Mapped[int] = mapped_column(Integer)  # drag & drop ordering
    sets: Mapped[int] = mapped_column(Integer, default=3)
    rep_range_min: Mapped[int | None] = mapped_column(default=None)
    rep_range_max: Mapped[int | None] = mapped_column(default=None)
    rest_seconds: Mapped[int | None] = mapped_column(default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    template: Mapped[WorkoutTemplate] = relationship(back_populates="exercises")


# ----------------------------------------------------------------- sessions


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str | None] = mapped_column(String(120), default=None)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_templates.id"), default=None
    )
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(default=None)

    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.position",
    )


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "position", name="uq_workout_exercise_session_position"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("workout_sessions.id", ondelete="CASCADE"), index=True
    )
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    position: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    session: Mapped[WorkoutSession] = relationship(back_populates="exercises")
    exercise: Mapped["Exercise"] = relationship()  # noqa: F821
    sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="workout_exercise",
        cascade="all, delete-orphan",
        order_by="WorkoutSet.set_number",
    )


class WorkoutSet(Base):
    __tablename__ = "workout_sets"
    __table_args__ = (
        CheckConstraint("reps >= 0", name="reps_nonnegative"),
        CheckConstraint(
            "(exercise_kind = 'duration') OR (reps IS NOT NULL)",
            name="reps_required_unless_duration",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_exercise_id: Mapped[int] = mapped_column(
        ForeignKey("workout_exercises.id", ondelete="CASCADE"), index=True
    )

    # Denormalized kind so sparse columns can be validated without joins:
    # weight | bodyweight | bodyweight_weighted | duration
    exercise_kind: Mapped[str] = mapped_column(String(24))

    set_number: Mapped[int] = mapped_column(Integer)

    # External load (free weight / machine / cable) — NULL otherwise.
    weight: Mapped[float | None] = mapped_column(Float, default=None)

    # Dumbbell semantics (spec §3 Type B): per_dumbbell=True means `weight`
    # is the per-dumbbell number; total external load = weight × pair count.
    per_dumbbell: Mapped[bool | None] = mapped_column(default=None)

    # Bodyweight work (spec §19) — stored separately, never faked.
    bodyweight: Mapped[float | None] = mapped_column(Float, default=None)
    added_weight: Mapped[float | None] = mapped_column(Float, default=None)

    # Timed holds (spec §3 Type E) — seconds; NULL otherwise.
    duration: Mapped[float | None] = mapped_column(Float, default=None)

    reps: Mapped[int | None] = mapped_column(Integer, default=None)

    # bodyweight | bodyweight_weighted | external | duration (set-level
    # resolution of the resistance type the user actually chose).
    resistance_type: Mapped[str | None] = mapped_column(String(24), default=None)

    # machine | plate_loaded | weight_stack (spec §3 Type C question).
    machine_type: Mapped[str | None] = mapped_column(String(20), default=None)
    machine_name: Mapped[str | None] = mapped_column(String(120), default=None)

    # stack setting vs actual selected weight (spec §3 Type D question).
    stack_value: Mapped[float | None] = mapped_column(Float, default=None)

    rest_time: Mapped[int | None] = mapped_column(Integer, default=None)  # seconds
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    # tempo e.g. "3-1-1" (progression dimension, spec §5).
    tempo: Mapped[str | None] = mapped_column(String(20), default=None)

    workout_exercise: Mapped[WorkoutExercise] = relationship(back_populates="sets")
