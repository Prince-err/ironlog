"""User, profile and state models: users, settings, bodyweight log, streaks,
PRs, mission completion, machine profiles, exercise notes."""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    bodyweight_kg: Mapped[float | None] = mapped_column(Float, default=None)
    unit: Mapped[str] = mapped_column(String(3), default="kg")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UserSettings(Base):
    """Per-user display preferences (spec §20: unit switching)."""

    __tablename__ = "user_settings"
    __table_args__ = (
        CheckConstraint("unit IN ('kg', 'lb')", name="unit_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    unit: Mapped[str] = mapped_column(String(3), default="kg")
    default_rest_seconds: Mapped[int] = mapped_column(default=90)


class BodyweightLog(Base):
    """Daily bodyweight entries — required context for bodyweight lifts."""

    __tablename__ = "bodyweight_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "log_date", name="uq_bodyweight_user_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    log_date: Mapped[date] = mapped_column(Date)
    weight_kg: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StreakState(Base):
    """Current streak bookkeeping (recomputable; cached here for speed)."""

    __tablename__ = "streak_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    current_streak: Mapped[int] = mapped_column(default=0)
    longest_streak: Mapped[int] = mapped_column(default=0)
    last_workout_date: Mapped[date | None] = mapped_column(Date, default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PersonalRecord(Base):
    """Best-known values per (user, exercise). Recomputed from history."""

    __tablename__ = "personal_records"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "exercise_id", "category", name="uq_pr_user_exercise_category"
        ),
        CheckConstraint(
            "category IN ('heaviest_weight', 'most_reps', 'best_1rm', "
            "'best_volume_set', 'longest_duration', 'most_reps_bodyweight', "
            "'most_reps_weighted', 'highest_added_weight')",
            name="pr_category_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(30))
    value: Mapped[float] = mapped_column(Float)
    weight: Mapped[float | None] = mapped_column(Float, default=None)
    reps: Mapped[int | None] = mapped_column(Integer, default=None)
    added_weight: Mapped[float | None] = mapped_column(Float, default=None)
    bodyweight: Mapped[float | None] = mapped_column(Float, default=None)
    duration: Mapped[float | None] = mapped_column(Float, default=None)
    set_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_sets.id", ondelete="SET NULL"), default=None
    )
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_sessions.id", ondelete="SET NULL"), default=None
    )
    achieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MissionCompletion(Base):
    """A daily mission offered to the user and its completion state."""

    __tablename__ = "mission_completions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    mission_date: Mapped[date] = mapped_column(Date, index=True)
    code: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(String(255))
    progress: Mapped[float] = mapped_column(Float, default=0)
    target: Mapped[float] = mapped_column(Float, default=1)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        UniqueConstraint("user_id", "mission_date", "code", name="uq_mission_daily"),
    )


class MachineProfile(Base):
    """Gym machines the user actually uses (spec §3 Type C labelling)."""

    __tablename__ = "machine_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_machine_profile_user_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    brand: Mapped[str | None] = mapped_column(String(120), default=None)
    machine_type: Mapped[str | None] = mapped_column(String(20), default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)


class ExerciseNote(Base):
    """Free-form personal notes per exercise (spec §14)."""

    __tablename__ = "exercise_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), index=True
    )
    note: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "exercise_id", name="uq_exercise_note"),
    )
