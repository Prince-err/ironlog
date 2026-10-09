"""Progressive overload recommendation engine (spec §5, §24, §25).

Given an exercise and its chronological set history, produce a
conservative, data-grounded recommendation for the next session.

Rules (never aggressively increase weight):
- Hit the top of the target rep range on (almost) all sets -> suggest a small
  load increase (smallest sensible plate jump) or more reps if bodyweight.
- Reps flat -> "match last time, add 1 rep on the final set".
- Reps falling -> maintain weight; suggest extra rest or keeping the load.
- Stalled for 3+ sessions at the same top weight -> vary the suggestion
  (add a rep, add a set, or reduce load slightly and rebuild).
- Duration exercises -> suggest +5s or an added hold.

Every suggestion is a suggestion: the user can override it in the UI.
"""

from dataclasses import dataclass, field

from app.models.workout import WorkoutSet

from app.services.metrics import effective_load


@dataclass
class SetSuggestion:
    weight: float | None = None
    reps: int | None = None
    duration: float | None = None
    bodyweight: float | None = None
    added_weight: float | None = None


@dataclass
class OverloadRecommendation:
    action: str                     # increase_weight | add_reps | maintain | deload | add_duration | progress_bodyweight
    headline: str
    detail: str
    target: list[SetSuggestion] = field(default_factory=list)
    confidence: str = "medium"      # low | medium | high


def _top_weight(sets: list[WorkoutSet]) -> float | None:
    loads = [effective_load(s) for s in sets]
    loads = [x for x in loads if x is not None]
    return max(loads) if loads else None


def _next_plate(weight: float) -> float:
    """Smallest sensible load jump: 2.5 kg steps (1.25 under 10 kg)."""
    if weight < 10:
        return round(weight + 1.25, 2)
    return round(weight + 2.5, 2)


def recommend(
    history: list[list[WorkoutSet]],
    rep_range: tuple[int, int] | None = None,
    target_sets: int | None = None,
) -> OverloadRecommendation | None:
    """Build a recommendation from chronological per-session set lists.

    `history` is ordered oldest -> newest; the last entry is the most
    recent session for this exercise.
    """
    if not history:
        return None
    last = history[-1]
    if not last:
        return None

    kind = last[0].exercise_kind

    if kind == "duration":
        return _recommend_duration(history)

    if kind in ("bodyweight", "bodyweight_weighted"):
        return _recommend_bodyweight(history, rep_range, target_sets)

    return _recommend_weighted(history, rep_range, target_sets)


# ---------------------------------------------------------------- duration


def _recommend_duration(history: list[list[WorkoutSet]]) -> OverloadRecommendation:
    last = history[-1]
    durations = [s.duration or 0 for s in last]
    best = max(durations) if durations else 0
    prev_best = None
    if len(history) >= 2 and history[-2]:
        prev_best = max(s.duration or 0 for s in history[-2])

    target = best + 5
    if prev_best is not None and best <= prev_best:
        action, headline = (
            "maintain",
            f"Hold {int(best)}s again — beat it with +5s when ready",
        )
    else:
        action, headline = "add_duration", f"Next hold: {int(target)}s"

    return OverloadRecommendation(
        action=action,
        headline=headline,
        detail=f"Last time: {', '.join(f'{int(d)}s' for d in durations)}. "
        "Progress holds in 5s steps.",
        target=[SetSuggestion(duration=target, reps=None)],
        confidence="high" if prev_best is not None else "medium",
    )


# --------------------------------------------------------------- bodyweight


def _recommend_bodyweight(
    history: list[list[WorkoutSet]],
    rep_range: tuple[int, int] | None,
    target_sets: int | None,
) -> OverloadRecommendation:
    last = history[-1]
    last_reps = [s.reps or 0 for s in last]
    top = max(last_reps) if last_reps else 0
    sets_count = len(last)

    # Added-weight variant: if the user has been training weighted, suggest
    # continuing the weighted pattern.
    weighted_sets = [s for s in last if s.added_weight]
    if weighted_sets:
        added = max(s.added_weight for s in weighted_sets) or 0
        bw = weighted_sets[0].bodyweight
        target = [
            SetSuggestion(
                bodyweight=bw,
                added_weight=added,
                reps=(min(r + 0, top) for r in [top]).__next__(),
            )
        ] * (target_sets or sets_count)
        # If they hit top of range consistently, add weight.
        if rep_range and top >= rep_range[1] and all(
            r >= rep_range[1] for r in last_reps
        ):
            new_added = _next_plate(added)
            return OverloadRecommendation(
                action="increase_weight",
                headline=(
                    f"You're consistently hitting {top} reps. "
                    f"Consider adding {new_added - added:.1f} kg."
                ),
                detail=f"Last: {top} reps with {added} kg added. "
                f"Next: {new_added} kg added × {rep_range[0]}-{top} reps.",
                target=[
                    SetSuggestion(
                        bodyweight=bw, added_weight=new_added, reps=rep_range[0]
                    )
                ]
                * (target_sets or sets_count),
                confidence="high",
            )
        return OverloadRecommendation(
            action="add_reps",
            headline=f"Match {added} kg × {top} reps, +1 on the last set",
            detail=f"Last: {', '.join(str(r) for r in last_reps)} reps at {added} kg added.",
            target=target,
            confidence="medium",
        )

    # Pure bodyweight: grow reps.
    if rep_range and top >= rep_range[1] and all(r >= rep_range[1] for r in last_reps):
        return OverloadRecommendation(
            action="progress_bodyweight",
            headline=(
                f"You're consistently hitting {top} reps. "
                "Consider adding 2.5 kg."
            ),
            detail=f"Last: {', '.join(str(r) for r in last_reps)}. "
            "Adding weight makes reps meaningful again.",
            target=[
                SetSuggestion(added_weight=2.5, reps=rep_range[0])
            ]
            * (target_sets or sets_count),
            confidence="high",
        )

    prev_top = None
    if len(history) >= 2 and history[-2]:
        prev_top = max(s.reps or 0 for s in history[-2])
    if prev_top is not None and top < prev_top:
        return OverloadRecommendation(
            action="maintain",
            headline=f"Reps dipped ({prev_top} → {top}). Match last time, don't force more.",
            detail=f"Last: {', '.join(str(r) for r in last_reps)} reps.",
            target=[SetSuggestion(reps=r) for r in last_reps],
            confidence="high",
        )

    goal = top + 1
    target_reps = last_reps[:-1] + [goal]
    return OverloadRecommendation(
        action="add_reps",
        headline=f"Match last time, then {goal} reps on the final set",
        detail=f"Last: {', '.join(str(r) for r in last_reps)} reps.",
        target=[SetSuggestion(reps=r) for r in target_reps],
        confidence="medium",
    )


# ----------------------------------------------------------------- weighted


def _recommend_weighted(
    history: list[list[WorkoutSet]],
    rep_range: tuple[int, int] | None,
    target_sets: int | None,
) -> OverloadRecommendation:
    last = history[-1]
    per_dumbbell = bool(last[0].per_dumbbell)
    top = _top_weight(last)
    if top is None:
        return OverloadRecommendation(
            action="maintain",
            headline="Log this lift once to unlock recommendations",
            detail="No load data yet.",
        )

    last_reps = [s.reps or 0 for s in last]
    sets_count = len(last)
    n_target = target_sets or sets_count
    lo, hi = rep_range if rep_range else (max(1, min(last_reps) - 2), max(last_reps))
    per = " per dumbbell" if per_dumbbell else ""

    def fmt(w: float) -> str:
        return f"{_trim(w)} kg{per}"

    def fmt_set(w: float, r: int) -> str:
        return f"{_trim(w)} × {r}"

    # 1) Top of the rep range hit on (almost) all sets -> increase load.
    if all(r >= hi for r in last_reps):
        new_w = _next_plate(top)
        return OverloadRecommendation(
            action="increase_weight",
            headline=f"You hit all reps. Try {fmt(new_w)} next session.",
            detail=f"Last session: {', '.join(fmt_set(top, r) for r in last_reps)}. "
            f"Next target: {fmt_set(new_w, lo)}-{hi}.",
            target=[SetSuggestion(weight=new_w, reps=lo)] * n_target,
            confidence="high",
        )

    # 2) Reps falling across sets but a solid base -> match last time.
    prev = history[-2] if len(history) >= 2 and history[-2] else None
    prev_top_weight = _top_weight(prev) if prev else None
    prev_reps = [s.reps or 0 for s in prev] if prev else []

    stalled = (
        prev_top_weight is not None
        and abs(prev_top_weight - top) < 0.01
        and len(history) >= 3
        and all(
            _top_weight(h) is not None and abs((_top_weight(h) or 0) - top) < 0.01
            for h in history[-3:]
        )
    )

    if stalled and not all(r >= lo for r in last_reps):
        return OverloadRecommendation(
            action="deload",
            headline=f"Stuck at {fmt(top)} for 3 sessions. Options: "
            "add 1 rep, drop the load slightly, or rest longer between sets.",
            detail=f"Recent sessions at {fmt(top)}: "
            + " | ".join(
                ", ".join(str(s.reps or 0) for s in h) for h in history[-3:]
            ),
            target=[SetSuggestion(weight=top, reps=max(lo, min(last_reps)))] * n_target,
            confidence="medium",
        )

    if prev_reps and all(a >= b for a, b in zip(last_reps, prev_reps)) and last_reps != prev_reps:
        # improved within range: keep the load, chase the top of range
        return OverloadRecommendation(
            action="add_reps",
            headline=f"Match {fmt(top)}, push each set +1 rep toward {hi}",
            detail=f"Last session: {', '.join(fmt_set(top, r) for r in last_reps)}. "
            f"Next session target: {', '.join(fmt_set(top, min(r + 1, hi)) for r in last_reps)}.",
            target=[
                SetSuggestion(weight=top, reps=min(r + 1, hi)) for r in last_reps
            ],
            confidence="high",
        )

    if any(r < lo for r in last_reps):
        return OverloadRecommendation(
            action="maintain",
            headline=f"Stay at {fmt(top)} and stabilize your reps first",
            detail=f"Last session: {', '.join(fmt_set(top, r) for r in last_reps)}. "
            "Aim to bring every set up to at least "
            f"{lo} reps before adding weight.",
            target=[SetSuggestion(weight=top, reps=lo)] * n_target,
            confidence="high",
        )

    # 3) Default conservative nudge: +1 rep on the final set.
    target_reps = last_reps[:-1] + [last_reps[-1] + 1]
    return OverloadRecommendation(
        action="add_reps",
        headline=f"Match {fmt(top)}, +1 rep on the last set",
        detail=f"Last session: {', '.join(fmt_set(top, r) for r in last_reps)}. "
        f"Next session target: {', '.join(fmt_set(top, r) for r in target_reps)}.",
        target=[SetSuggestion(weight=top, reps=r) for r in target_reps],
        confidence="medium",
    )


def _trim(w: float) -> str:
    return str(int(w)) if float(w).is_integer() else f"{w:g}"
