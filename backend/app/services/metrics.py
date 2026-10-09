"""Set-level metric helpers shared by all engines.

A WorkoutSet can represent weight sets, bodyweight sets, weighted-bodyweight
sets or timed holds. These helpers compute normalized metrics:

- effective load ("total resistance"): what the user actually moved
- set volume: load × reps
- estimated 1RM (Epley formula, clearly labelled as an estimate)
"""

from app.models.workout import WorkoutSet


def effective_load(s: WorkoutSet) -> float | None:
    """Total external resistance moved for this set, or None if not load-based.

    - weight sets: per_dumbbell weight × 2 (pair), else the raw weight
    - bodyweight_weighted: bodyweight + added_weight
    - bodyweight: bodyweight (constant across sets; still useful for volume)
    - duration: None
    """
    if s.exercise_kind == "duration":
        return None
    if s.exercise_kind == "weight":
        if s.weight is None:
            return None
        return float(s.weight) * 2 if s.per_dumbbell else float(s.weight)
    if s.exercise_kind == "bodyweight_weighted":
        total = 0.0
        if s.bodyweight is not None:
            total += float(s.bodyweight)
        if s.added_weight is not None:
            total += float(s.added_weight)
        return total if (s.bodyweight or s.added_weight) else None
    if s.exercise_kind == "bodyweight":
        return float(s.bodyweight) if s.bodyweight is not None else None
    return None


def set_volume(s: WorkoutSet) -> float:
    """Volume for one set: effective load × reps (0 for timed holds)."""
    load = effective_load(s)
    if load is None or s.reps is None:
        return 0.0
    return load * s.reps


def estimated_1rm(weight: float | None, reps: int | None) -> float | None:
    """Epley estimated 1RM — an ESTIMATE, never a measured max (spec §25)."""
    if not weight or not reps or reps <= 0:
        return None
    return round(weight * (1 + reps / 30), 1)


def best_set_1rm(sets: list[WorkoutSet]) -> float | None:
    """Highest estimated 1RM across sets (weight-based sets only)."""
    best: float | None = None
    for s in sets:
        load = effective_load(s)
        e = estimated_1rm(load, s.reps)
        if e is not None and (best is None or e > best):
            best = e
    return best


def total_volume(sets: list[WorkoutSet]) -> float:
    return sum(set_volume(s) for s in sets)
