"""SQLAlchemy models for Iron Log.

All model modules are imported here so that create_all / future Alembic
autogenerate sees the complete metadata.
"""

from app.models.association import ExerciseMuscle, ExerciseVariation
from app.models.exercise import Exercise
from app.models.reference import Equipment, MuscleGroup
from app.models.user import (
    BodyweightLog,
    ExerciseNote,
    MachineProfile,
    MissionCompletion,
    PersonalRecord,
    StreakState,
    User,
    UserSettings,
)
from app.models.workout import (
    TemplateExercise,
    WorkoutExercise,
    WorkoutSession,
    WorkoutSet,
    WorkoutTemplate,
)

__all__ = [
    "BodyweightLog",
    "Equipment",
    "Exercise",
    "ExerciseMuscle",
    "ExerciseNote",
    "ExerciseVariation",
    "MachineProfile",
    "MissionCompletion",
    "MuscleGroup",
    "PersonalRecord",
    "StreakState",
    "TemplateExercise",
    "User",
    "UserSettings",
    "WorkoutExercise",
    "WorkoutSession",
    "WorkoutSet",
    "WorkoutTemplate",
]
