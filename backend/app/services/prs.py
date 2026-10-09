"""Personal record detection (spec §8).

PRs are always recomputed from set history — never invented. Categories:

Weight-based lifts: heaviest_weight, most_reps, best_1rm,
best_volume_set.
Bodyweight: most_reps_bodyweight, most_reps_weighted,
highest_added_weight.
Duration: longest_duration.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.exercise import Exercise
from app.models.workout import WorkoutExercise, WorkoutSession, WorkoutSet

from app.services.metrics import effective_load, estimated_1rm, set_volume

CATEGORIES_WEIGHTED = ("heaviest_weight", "most_reps", "best_1rm", "best_volume_set")
CATEGORIES_BODYWEIGHT = ("most_reps_bodyweight", "most_reps_weighted", "highest_added_weight")
CATEGORIES_DURATION = ("longest_duration",)


@dataclass
class PRCandidate:
    category: str
    value: float
    weight: float | None = None
    reps: int | None = None
    added_weight: float | None = None
    bodyweight: float | None = None
    duration: float | None = None
    set_id: int | None = None
    session_id: int | None = None
    achieved_at: object = None


def compute_prs_for_sets(sets: list[WorkoutSet]) -> list[PRCandidate]:
    """Best PR candidates across a list of sets (one per category)."""
    out: dict[str, PRCandidate] = {}

    def consider(c: PRCandidate) -> None:
        cur = out.get(c.category)
        if cur is None or c.value > cur.value:
            out[c.category] = c

    for s in sets:
        load = effective_load(s)
        if s.exercise_kind == "duration":
            if s.duration:
                consider(
                    PRCandidate(
                        "longest_duration", float(s.duration), duration=s.duration,
                        set_id=s.id, achieved_at=s.completed_at,
                    )
                )
            continue

        if s.reps is None:
            continue
        reps = s.reps

        if s.exercise_kind == "weight":
            if load is not None:
                consider(
                    PRCandidate(
                        "heaviest_weight", load, weight=load, reps=reps,
                        set_id=s.id, achieved_at=s.completed_at,
                    )
                )
                consider(
                    PRCandidate(
                        "most_reps", float(reps), weight=load, reps=reps,
                        set_id=s.id, achieved_at=s.completed_at,
                    )
                )
                e = estimated_1rm(load, reps)
                if e:
                    consider(
                        PRCandidate(
                            "best_1rm", e, weight=load, reps=reps,
                            set_id=s.id, achieved_at=s.completed_at,
                        )
                    )
                consider(
                    PRCandidate(
                        "best_volume_set", set_volume(s), weight=load, reps=reps,
                        set_id=s.id, achieved_at=s.completed_at,
                    )
                )
        elif s.exercise_kind == "bodyweight":
            consider(
                PRCandidate(
                    "most_reps_bodyweight", float(reps), reps=reps,
                    bodyweight=s.bodyweight,
                    set_id=s.id, achieved_at=s.completed_at,
                )
            )
        elif s.exercise_kind == "bodyweight_weighted":
            consider(
                PRCandidate(
                    "most_reps_weighted", float(reps), reps=reps,
                    added_weight=s.added_weight, bodyweight=s.bodyweight,
                    set_id=s.id, achieved_at=s.completed_at,
                )
            )
            if s.added_weight:
                consider(
                    PRCandidate(
                        "highest_added_weight", float(s.added_weight),
                        reps=reps, added_weight=s.added_weight,
                        bodyweight=s.bodyweight,
                        set_id=s.id, achieved_at=s.completed_at,
                    )
                )

    return list(out.values())


def recompute_user_prs(db: Session, user_id: int, exercise_id: int) -> list[PRCandidate]:
    """Recompute and persist PR rows for one (user, exercise)."""
    from app.models.user import PersonalRecord

    sets = db.scalars(
        select(WorkoutSet)
        .join(WorkoutExercise, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
        .join(WorkoutSession, WorkoutExercise.session_id == WorkoutSession.id)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutExercise.exercise_id == exercise_id,
            WorkoutSession.status == "completed",
        )
    ).all()

    best: dict[str, PRCandidate] = {}
    for c in compute_prs_for_sets(sets):
        cur = best.get(c.category)
        if cur is None or c.value > cur.value:
            best[c.category] = c

    existing = {
        pr.category: pr
        for pr in db.scalars(
            select(PersonalRecord).where(
                PersonalRecord.user_id == user_id,
                PersonalRecord.exercise_id == exercise_id,
            )
        ).all()
    }

    new_prs: list[PRCandidate] = []
    for category, cand in best.items():
        row = existing.get(category)
        if row is None or cand.value > row.value:
            new_prs.append(cand)
            if row is None:
                row = PersonalRecord(user_id=user_id, exercise_id=exercise_id, category=category)
                db.add(row)
            row.value = cand.value
            row.weight = cand.weight
            row.reps = cand.reps
            row.added_weight = cand.added_weight
            row.bodyweight = cand.bodyweight
            row.duration = cand.duration
            row.set_id = cand.set_id
            row.session_id = cand.session_id
            row.achieved_at = cand.achieved_at

    db.flush()
    return new_prs
