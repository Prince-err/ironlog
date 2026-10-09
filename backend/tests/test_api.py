"""API tests for Iron Log — run against isolated in-memory SQLite."""

from datetime import date

from app.db.exercise_data import EXERCISES


def _find_exercise(client, headers, name):
    r = client.get("/api/v1/exercises", headers=headers)
    assert r.status_code == 200
    for e in r.json():
        if e["name"] == name:
            return e
    raise AssertionError(f"exercise {name!r} not in library")


def _start_session(client, headers, exercise_names):
    ids = [_find_exercise(client, headers, n)["id"] for n in exercise_names]
    r = client.post(
        "/api/v1/sessions/start",
        headers=headers,
        json={"exercise_ids": ids, "name": "Test"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _log_weight_set(client, headers, wid, weight, reps):
    r = client.post(
        f"/api/v1/workout-exercises/{wid}/sets",
        headers=headers,
        json={"weight": weight, "reps": reps},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------- library


class TestExerciseLibrary:
    def test_catalog_is_large(self, client, headers):
        r = client.get("/api/v1/exercises", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) >= 150
        names = {e["name"] for e in r.json()}
        assert "Bench Press" in names
        assert "Pull-Ups" in names
        assert "Plank" in names

    def test_filter_by_group_and_search(self, client, headers):
        r = client.get("/api/v1/exercises", headers=headers,
                       params={"group": "Chest"})
        names = {e["name"] for e in r.json()}
        assert "Bench Press" in names
        assert "Barbell Curl" not in names

        r = client.get("/api/v1/exercises", headers=headers, params={"q": "bench"})
        assert all("bench" in e["name"].lower() for e in r.json())

    def test_requires_identity(self, client):
        assert client.get("/api/v1/exercises").status_code == 401

    def test_create_custom_exercise(self, client, headers):
        r = client.post("/api/v1/exercises", headers=headers, json={
            "name": "Landmine Squat Press", "exercise_type": "free_weight",
            "resistance": "external",
        })
        assert r.status_code == 201
        # searchable right away
        r = client.get("/api/v1/exercises", headers=headers, params={"q": "landmine squat"})
        assert any(e["name"] == "Landmine Squat Press" for e in r.json())


# ------------------------------------------------------------- logging loop


class TestWorkoutLoop:
    def test_full_session_lifecycle(self, client, headers):
        session = _start_session(client, headers, ["Bench Press", "Plank"])
        sid = session["id"]
        we_bench = session["exercises"][0]["workout_exercise_id"]
        we_plank = session["exercises"][1]["workout_exercise_id"]

        # log bench sets
        _log_weight_set(client, headers, we_bench, 80, 8)
        _log_weight_set(client, headers, we_bench, 80, 8)
        # log plank (duration — no weight/reps required)
        r = client.post(f"/api/v1/workout-exercises/{we_plank}/sets",
                        headers=headers, json={"duration": 45})
        assert r.status_code == 201
        assert r.json()["duration"] == 45
        assert r.json()["reps"] is None  # sparse — no fake values

        r = client.post(f"/api/v1/sessions/{sid}/complete", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body["sets"] == 3
        assert body["exercises"] == 2
        assert body["volume"] > 0
        assert "streak" in body

        # session is now completed; active list empty
        r = client.get("/api/v1/sessions/active", headers=headers)
        assert r.json() is None

    def test_plank_does_not_require_weight(self, client, headers):
        """Spec §18/§25: a plank must not need a weight field."""
        session = _start_session(client, headers, ["Plank"])
        we = session["exercises"][0]["workout_exercise_id"]
        r = client.post(f"/api/v1/workout-exercises/{we}/sets",
                        headers=headers, json={"duration": 60})
        assert r.status_code == 201

    def test_weight_set_requires_weight(self, client, headers):
        session = _start_session(client, headers, ["Bench Press"])
        we = session["exercises"][0]["workout_exercise_id"]
        r = client.post(f"/api/v1/workout-exercises/{we}/sets",
                        headers=headers, json={"reps": 8})
        assert r.status_code == 422

    def test_previous_performance_and_recommendation(self, client, headers):
        # first workout
        session = _start_session(client, headers, ["Bench Press"])
        we = session["exercises"][0]["workout_exercise_id"]
        _log_weight_set(client, headers, we, 60, 10)
        _log_weight_set(client, headers, we, 60, 10)
        client.post(f"/api/v1/sessions/{session['id']}/complete", headers=headers)

        # second workout: previous performance is available
        session2 = _start_session(client, headers, ["Bench Press"])
        we2 = session2["exercises"][0]["workout_exercise_id"]
        r = client.get(f"/api/v1/exercises/{session2['exercises'][0]['exercise_id']}/previous",
                       headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body["sets"][0]["weight"] == 60
        assert body["recommendation"] is not None

        # hit top of range -> recommendation suggests +2.5
        _log_weight_set(client, headers, we2, 60, 10)
        _log_weight_set(client, headers, we2, 60, 10)
        client.post(f"/api/v1/sessions/{session2['id']}/complete", headers=headers)

        session3 = _start_session(client, headers, ["Bench Press"])
        r = client.get(f"/api/v1/exercises/{session3['exercises'][0]['exercise_id']}/previous",
                       headers=headers)
        rec = r.json()["recommendation"]
        assert rec["action"] == "increase_weight"
        assert rec["target"][0]["weight"] == 62.5

    def test_weighted_bodyweight_separates_fields(self, client, headers):
        """Spec §19: bodyweight / added weight / total stored separately."""
        session = _start_session(client, headers, ["Weighted Pull-Ups"])
        we = session["exercises"][0]["workout_exercise_id"]
        r = client.post(f"/api/v1/workout-exercises/{we}/sets", headers=headers, json={
            "reps": 8, "added_weight": 10, "bodyweight": 78,
        })
        assert r.status_code == 201
        body = r.json()
        assert body["bodyweight"] == 78
        assert body["added_weight"] == 10
        assert body["exercise_kind"] == "bodyweight_weighted"

    def test_only_one_active_session(self, client, headers):
        _start_session(client, headers, ["Bench Press"])
        r = client.post("/api/v1/sessions/start", headers=headers,
                        json={"exercise_ids": [1]})
        assert r.status_code == 409

    def test_history_page(self, client, headers):
        ex = _find_exercise(client, headers, "Bench Press")
        r = client.get(f"/api/v1/exercises/{ex['id']}/history", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert len(body["sessions"]) == 5  # seeded history
        assert body["totals"]["sessions"] == 5
        assert body["bests"]["heaviest_weight"] == 80.0

    def test_history_range_filter(self, client, headers):
        ex = _find_exercise(client, headers, "Bench Press")
        r = client.get(f"/api/v1/exercises/{ex['id']}/history",
                       headers=headers, params={"range": "7d"})
        assert r.status_code == 200
        for sess in r.json()["sessions"]:
            assert sess["date"] >= str(date.today().replace(day=date.today().day - 7))


# ----------------------------------------------------------------- PRs


class TestPRs:
    def test_pr_detected_on_completion(self, client, headers):
        session = _start_session(client, headers, ["Bench Press"])
        we = session["exercises"][0]["workout_exercise_id"]
        _log_weight_set(client, headers, we, 85, 5)  # beats seeded 80
        client.post(f"/api/v1/sessions/{session['id']}/complete", headers=headers)

        r = client.get("/api/v1/prs", headers=headers)
        assert r.status_code == 200
        bench = next(p for p in r.json() if p["exercise"] == "Bench Press")
        cats = {rec["category"]: rec for rec in bench["records"]}
        assert cats["heaviest_weight"]["weight"] == 85

    def test_prs_page_after_seeded_history(self, client, headers):
        r = client.get("/api/v1/prs", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) >= 5


# ------------------------------------------------------------- templates


class TestTemplates:
    def test_seeded_templates_exist(self, client, headers):
        r = client.get("/api/v1/templates", headers=headers)
        names = {t["name"] for t in r.json()}
        assert {"Push", "Pull", "Legs"} <= names

    def test_start_from_template(self, client, headers):
        templates = client.get("/api/v1/templates", headers=headers).json()
        push = next(t for t in templates if t["name"] == "Push")
        r = client.post("/api/v1/sessions/start", headers=headers,
                        json={"template_id": push["id"]})
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Push"
        assert len(body["exercises"]) == 5

    def test_repeat_last_snapshot(self, client, headers):
        templates = client.get("/api/v1/templates", headers=headers).json()
        push = next(t for t in templates if t["name"] == "Push")
        r = client.get(f"/api/v1/templates/{push['id']}/previous", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body is not None
        assert len(body["exercises"]) == 5
        assert body["exercises"][0]["sets"][0]["weight"] is not None

    def test_create_and_reorder_template(self, client, headers):
        ex_a = _find_exercise(client, headers, "Bench Press")["id"]
        ex_b = _find_exercise(client, headers, "Barbell Curl")["id"]
        r = client.post("/api/v1/templates", headers=headers, json={
            "name": "Test Day",
            "exercises": [
                {"exercise_id": ex_a, "sets": 3, "rep_range_min": 8,
                 "rep_range_max": 12, "rest_seconds": 150},
                {"exercise_id": ex_b, "sets": 3},
            ],
        })
        assert r.status_code == 201
        tid = r.json()["id"]
        first_item = r.json()["exercises"][0]["id"]

        # move first to end
        r = client.put(f"/api/v1/templates/{tid}/reorder", headers=headers,
                       json={"item_id": first_item, "new_position": 1})
        assert r.status_code == 200
        assert r.json()["exercises"][0]["name"] == "Barbell Curl"


# ---------------------------------------------------------- dashboard etc


class TestDashboardAndAnalytics:
    def test_dashboard_payload(self, client, headers):
        r = client.get("/api/v1/dashboard", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body["streak"]["current_streak"] >= 1
        assert body["mission"] is not None
        assert len(body["missions"]) >= 3

    def test_heatmap(self, client, headers):
        r = client.get("/api/v1/heatmap", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 180
        assert any(d["workouts"] > 0 for d in data)

    def test_analytics_summary(self, client, headers):
        r = client.get("/api/v1/analytics/summary",
                       headers=headers, params={"range": "30d"})
        body = r.json()
        assert body["sessions"] >= 3
        assert body["total_volume"] > 0

    def test_muscle_group_volume(self, client, headers):
        r = client.get("/api/v1/analytics/muscle-groups", headers=headers)
        groups = {g["muscle_group"] for g in r.json()}
        assert "Chest" in groups
        # squat/RDL/leg press roll up under quads/hamstrings (primary muscle)
        assert groups & {"Quads", "Hamstrings", "Glutes"}

    def test_recommendations_derived_from_data(self, client, headers):
        r = client.get("/api/v1/analytics/recommendations", headers=headers)
        assert r.status_code == 200
        assert isinstance(r.json()["recommendations"], list)

    def test_settings_unit_switch(self, client, headers):
        r = client.put("/api/v1/me", headers=headers, json={"unit": "lb"})
        assert r.json()["unit"] == "lb"
        r = client.put("/api/v1/me", headers=headers, json={"unit": "kg"})
        assert r.json()["unit"] == "kg"

    def test_bodyweight_log(self, client, headers):
        r = client.post("/api/v1/me/bodyweight", headers=headers,
                        json={"weight_kg": 78.4})
        assert r.status_code == 201
        r = client.get("/api/v1/me/bodyweight", headers=headers)
        assert r.json()[0]["weight_kg"] == 78.4

    def test_workout_history_list(self, client, headers):
        r = client.get("/api/v1/history", headers=headers)
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 15  # 5 weeks × 3 sessions
        assert all("volume" in row for row in rows)
