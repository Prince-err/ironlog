"""Many-to-many association between exercises and muscle groups."""

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExerciseMuscle(Base):
    __tablename__ = "exercise_muscles"
    __table_args__ = (
        UniqueConstraint("exercise_id", "muscle_group_id", name="uq_exercise_muscle"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), index=True
    )
    muscle_group_id: Mapped[int] = mapped_column(ForeignKey("muscle_groups.id"))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    exercise: Mapped["Exercise"] = relationship(back_populates="muscles")  # noqa: F821
    muscle_group: Mapped["MuscleGroup"] = relationship()  # noqa: F821


class ExerciseVariation(Base):
    """Named variation of an exercise (e.g. Grip: wide on Lat Pulldown)."""

    __tablename__ = "exercise_variations"

    id: Mapped[int] = mapped_column(primary_key=True)
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(default=None)
