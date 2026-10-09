"""Engine unit tests: metrics, overload rules, PR detection, streaks."""

from datetime import date, datetime, timedelta

from app.models.exercise import Exercise
from app.models.user import User
from app.models.workout import (
    WorkoutExercise,
    WorkoutSession,
    WorkoutSet,
)
from app.services.metrics import effective_load, estimated_1rm, set_volume
from app.services.overload import recommend
from app.services.streaks import compute_streak


def _make_set(kind="weight", weight=80.0, reps=8, per_dumbbell=None,
              bodyweight=None, added_weight=None, duration=None):
    s = WorkoutSet(
        workout_exercise_id=1,
        exercise_kind=kind,
        set_number=1,
        weight=weight if kind == "weight" else None,
        per_dumbbell=per_dumbbell,
        reps=reps,
        duration=duration,
        bodyweight=bodyweight,
        added_weight=added_weight,
    )
    return s


# ---------------------------------------------------------------- metrics


class TestMetrics:
    def test_per_dumbbell_doubles_total_load(self):
        s = _make_set(weight=20.0, per_dumbbell=True, reps=10)
        assert effective_load(s) == 40.0
        assert set_volume(s) == 400.0

    def test_barbell_weight_is_total(self):
        s = _make_set(weight=80.0, per_dumbbell=None, reps=8)
        assert effective_load(s) == 80.0
        assert set_volume(s) == 640.0

    def test_bodyweight_plus_added(self):
        s = _make_set(kind="bodyweight_weighted", bodyweight=50.0,
                      added_weight=10.0, reps=8)
        assert effective_load(s) == 60.0

    def test_duration_has_no_load(self):
        s = _make_set(kind="duration", duration=45)
        assert effective_load(s) is None
        assert set_volume(s) == 0.0

    def test_epley_1rm(self):
        assert estimated_1rm(100, 5) == 116.7
        assert estimated_1rm(None, 5) is None
        assert estimated_1rm(100, None) is None


# ------------------------------------------------------------- overload


class TestOverload:
    def test_all_reps_at_top_of_range_suggests_increase(self):
        history = [[_make_set(weight=60, reps=10), _make_set(weight=60, reps=10),
                    _make_set(weight=60, reps=10)]]
        rec = recommend(history, rep_range=(8, 10))
        assert rec.action == "increase_weight"
        assert rec.target[0].weight == 62.5

    def test_falling_reps_suggest_maintain(self):
        history = [
            [_make_set(weight=60, reps=12), _make_set(weight=60, reps=12),
             _make_set(weight=60, reps=12)],
            [_make_set(weight=60, reps=12), _make_set(weight=60, reps=10),
             _make_set(weight=60, reps=8)],
        ]
        rec = recommend(history, rep_range=(8, 12))
        assert rec.action in ("maintain", "add_reps")
        assert rec.target[0].weight == 60  # never increases blindly

    def test_never_recommends_big_jumps(self):
        history = [[_make_set(weight=100, reps=12), _make_set(weight=100, reps=12)]]
        rec = recommend(history, rep_range=(8, 12))
        assert rec.target[0].weight <= 102.5  # max +2.5 kg

    def test_bodyweight_reps_progression(self):
        history = [
            [_make_set(kind="bodyweight", bodyweight=78, reps=10),
             _make_set(kind="bodyweight", bodyweight=78, reps=10)],
            [_make_set(kind="bodyweight", bodyweight=78, reps=10),
             _make_set(kind="bodyweight", bodyweight=78, reps=10)],
        ]
        rec = recommend(history, rep_range=(6, 10))
        assert rec.action == "progress_bodyweight"
        assert "2.5 kg" in rec.headline

    def test_duration_progression(self):
        history = [[_make_set(kind="duration", duration=45),
                    _make_set(kind="duration", duration=45)]]
        rec = recommend(history)
        assert rec.action == "add_duration"
        assert rec.target[0].duration == 50

    def test_empty_history_returns_none(self):
        assert recommend([]) is None


# ---------------------------------------------------------------- streaks


class TestStreaks:
    def _fresh_user_with_exercise(self, db):
        """A user with no seeded history (avoids demo-data collisions)."""
        user = User(email="streaker@test.dev", name="Streak User")
        db.add(user)
        db.flush()
        exercise = db.query(Exercise).first()
        return user, exercise

    def test_streak_counts_completed_days(self, db_session):
        user, exercise = self._fresh_user_with_exercise(db_session)
        today = date.today()
        for offset in (0, 1, 2):
            day = today - timedelta(days=offset)
            s = WorkoutSession(
                user_id=user.id, name="T", status="completed",
                started_at=datetime(day.year, day.month, day.day, 18, 0),
                completed_at=datetime(day.year, day.month, day.day, 19, 0),
            )
            db_session.add(s)
            db_session.flush()
            we = WorkoutExercise(session_id=s.id, exercise_id=exercise.id, position=0)
            db_session.add(we)
            db_session.flush()
            db_session.add(WorkoutSet(
                workout_exercise_id=we.id, exercise_kind="weight",
                set_number=1, weight=60, reps=8,
            ))
        db_session.flush()

        info = compute_streak(db_session, user.id, today)
        assert info["current_streak"] == 3
        assert info["worked_out_today"] is True

    def test_rest_day_does_not_break_streak(self, db_session):
        user, exercise = self._fresh_user_with_exercise(db_session)
        today = date.today()
        # trained today and 2 days ago (rest yesterday)
        for offset in (0, 2):
            day = today - timedelta(days=offset)
            s = WorkoutSession(
                user_id=user.id, status="completed",
                started_at=datetime(day.year, day.month, day.day, 18, 0),
                completed_at=datetime(day.year, day.month, day.day, 19, 0),
            )
            db_session.add(s)
            db_session.flush()
            we = WorkoutExercise(session_id=s.id, exercise_id=exercise.id, position=0)
            db_session.add(we)
            db_session.flush()
            db_session.add(WorkoutSet(
                workout_exercise_id=we.id, exercise_kind="weight",
                set_number=1, weight=60, reps=8,
            ))
        db_session.flush()
        info = compute_streak(db_session, user.id, today)
        assert info["current_streak"] == 2  # rest day tolerated

    def test_no_sessions_zero_streak(self, db_session):
        user = User(email="fresh@test.dev", name="Fresh")
        db_session.add(user)
        db_session.flush()
        info = compute_streak(db_session, user.id)
        assert info["current_streak"] == 0
