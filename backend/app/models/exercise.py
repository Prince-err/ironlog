"""Exercise model.

An exercise carries its classification up front (see spec §3):

- exercise_type: bodyweight | free_weight | machine | cable | duration
- resistance: how load is interpreted for this exercise
  - bodyweight          (bodyweight only)
  - bodyweight_weighted (bodyweight + optional added weight)
  - external            (free weight / machine / cable — external load)
  - duration            (timed holds)

Muscle linkage is many-to-many with a "primary" flag; the primary muscle
drives muscle-group volume rollups.
"""

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.association import ExerciseMuscle

RESISTANCE_BODYWEIGHT = "bodyweight"
RESISTANCE_BODYWEIGHT_WEIGHTED = "bodyweight_weighted"
RESISTANCE_EXTERNAL = "external"
RESISTANCE_DURATION = "duration"


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = (
        # Custom user exercises may reuse a catalog name; seeded catalog rows
        # are unique by name to keep lookups deterministic.
        UniqueConstraint("name", "owner_user_id", name="uq_exercises_name_owner"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    # null => catalog exercise shared by everyone; set => private custom exercise
    owner_user_id: Mapped[int | None] = mapped_column(default=None, index=True)

    exercise_type: Mapped[str] = mapped_column(String(20))  # spec §3 types
    resistance: Mapped[str] = mapped_column(String(20))     # load interpretation
    primary_muscle_id: Mapped[int | None] = mapped_column(default=None, index=True)
    equipment_id: Mapped[int | None] = mapped_column(default=None)

    # Default per-dumbbell handling for free weights (spec §3 Type B):
    # dumbbell_pair=True means the logged number is per dumbbell.
    dumbbell_pair: Mapped[bool] = mapped_column(Boolean, default=False)

    # Machine exercises may carry a machine profile name (spec §3 Type C):
    # "Life Fitness Leg Press" etc. Null for catalog rows.
    default_machine: Mapped[str | None] = mapped_column(default=None)

    # Short form description + technique tips (spec §14).
    form_description: Mapped[str | None] = mapped_column(default=None)
    technique_tips: Mapped[str | None] = mapped_column(default=None)

    muscles: Mapped[list["ExerciseMuscle"]] = relationship(
        back_populates="exercise",
        cascade="all, delete-orphan",
        order_by="ExerciseMuscle.is_primary.desc()",
    )
