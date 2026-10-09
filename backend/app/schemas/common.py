"""Pydantic schemas for the Iron Log API."""

from pydantic import BaseModel, ConfigDict, Field


class SetIn(BaseModel):
    """One logged set. Sparse: only relevant fields are required."""

    weight: float | None = None
    reps: int | None = Field(default=None, ge=0)
    duration: float | None = Field(default=None, gt=0)
    bodyweight: float | None = None
    added_weight: float | None = None
    per_dumbbell: bool | None = None
    machine_type: str | None = None
    machine_name: str | None = None
    stack_value: float | None = None
    rest_time: int | None = None
    tempo: str | None = None
    notes: str | None = None


class SetUpdateIn(BaseModel):
    weight: float | None = None
    reps: int | None = Field(default=None, ge=0)
    duration: float | None = None
    rest_time: int | None = None
    notes: str | None = None


class StartSessionIn(BaseModel):
    template_id: int | None = None
    name: str | None = None
    exercise_ids: list[int] | None = None


class AddExerciseIn(BaseModel):
    exercise_id: int


class ReorderIn(BaseModel):
    new_position: int = Field(ge=0)


class CustomExerciseIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    exercise_type: str = "free_weight"
    resistance: str = "external"
    primary_muscle_id: int | None = None
    dumbbell_pair: bool = False
    form_description: str | None = None
    technique_tips: str | None = None


class TemplateExerciseIn(BaseModel):
    exercise_id: int
    sets: int = 3
    rep_range_min: int | None = None
    rep_range_max: int | None = None
    rest_seconds: int | None = None
    notes: str | None = None


class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    exercises: list[TemplateExerciseIn] = []


class TemplateReorderIn(BaseModel):
    item_id: int
    new_position: int = Field(ge=0)


class NoteIn(BaseModel):
    note: str


class BodyweightIn(BaseModel):
    weight_kg: float = Field(gt=0)
    log_date: str | None = None


class SettingsIn(BaseModel):
    unit: str | None = None
    default_rest_seconds: int | None = None
    bodyweight_kg: float | None = None
    name: str | None = None
